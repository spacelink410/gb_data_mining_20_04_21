import json
import time
from pathlib import Path
import requests


class MyParser:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36"
    }

    params = {"records_per_page": 20}

    category_dict = {"name": None, "code": None}

    def __init__(
        self, target_url: str, url_category: str, url_product: str, url_d: str, save_dir: Path
    ):
        self.target_url = target_url
        self.url_category = url_category
        self.save_dir = save_dir
        self.url_d = url_d
        self.url_product = url_product

    def get_response(self, url_in, *args, **kwargs):
        while True:
            response = requests.get(url_in, *args, **kwargs)
            if response.status_code == 200:
                return response

    def url_transform(self, url_in: str, url_d: str, url_s: str = ""):
        """Универсальный метод для сборки корректного url адреса. Реализован для конкретного класса MyParse и
        предназначен для того, чтобы формировать рабочий url из базовой и служебной части при первом входе,
        а в случае, если у портала осуществляется подмена домена, то исправление url на корректный

        :param url_in: Входной url адрес. Строка
        :param url_d: Делиметр, по которому будет разбиваться строка url_in для отделения осовного домена и служебной
            части адреса для api. При этом сам делиметр будет входить в служебную часть.
        :param url_s: служебная часть url адреса. Если метод используется для разделения адреса и замены домена на
            базовый, то данный параметр следует оставить пусты. Если наоборот для склейки оснвоного домена и служебной
            части url адреса, то в параметр следует передавать строку со служебнойчастью
        :return: Возвращает корректный адрес, собранный для использования
        """
        if url_in.find(url_d) != -1:
            url_in = url_in[url_in.find(url_d) :]
            url_out = "".join([self.target_url, url_in, url_s])
        else:
            url_out = "".join([self.target_url, url_s])

        return url_out

    def get_category(self, url_in: str, url_s: str):
        # трансформируем url по общему мезанизму
        url_in = self.url_transform(url_in, self.url_d, url_s) if url_in else url_in
        response = self.get_response(url_in, headers=self.headers)
        data = response.json()
        for category in data:
            yield category

    def get_products(self, url_in: str, url_s: str):
        while url_in:
            # преобразуем url в нужный формат api
            url_in = self.url_transform(url_in, self.url_d, url_s) if url_in else url_in
            # удалим служебную часть url, т.к. она нужна только при первм запросе, когда еще нет следующей страницы
            url_s = ""

            # направим запрос с параметрми и получим ответ
            time.sleep(0.1)
            response = self.get_response(url_in, headers=self.headers, params=self.params)
            data = response.json()

            # получим url следующей страницы
            url_in = data["next"]
            # получим продукты со страницы
            for product in data["results"]:
                yield product

    def parse(self):
        for category in self.get_category(self.target_url, self.url_category):
            # Добавим(обновим) в params код категории
            self.params.update({"categories": category["parent_group_code"]})

            # Добавим продукт
            product_list: list = []
            for product in self.get_products(self.target_url, self.url_product):
                product_list.append(product)

            # Сформируем финальных словарь для записи в файл
            self.category_dict.update(
                {
                    "name": category["parent_group_name"],
                    "code": category["parent_group_code"],
                    "products": product_list,
                }
            )

            # сформируем путь с именем файла код_категории_имя_категории
            file_path = self.save_dir.joinpath(
                f"{category['parent_group_code']}_{category['parent_group_name']}.json"
            )
            file_path.write_text(json.dumps(self.category_dict, ensure_ascii=False))


# функция проверки существования файла
def get_save_path(dir_name):
    save_dir = Path(__file__).parent.joinpath(dir_name)
    if not save_dir.exists():
        save_dir.mkdir()
    return save_dir


if __name__ == "__main__":
    # выберем директорию для сохранения результата
    save_path = get_save_path("catalog")

    # основной url ресурса
    t_url = "https://5ka.ru"

    # служеьная часть url для парсинга продуктов
    product_url = "/api/v2/special_offers/"
    # служеьная часть url для парсинга каотегорий
    category_url = "/api/v2/categories/"

    # делиметр для поска служебной части url
    d_url = "/api/v2/"

    parser = MyParser(t_url, category_url, product_url, d_url, save_path)
    parser.parse()
