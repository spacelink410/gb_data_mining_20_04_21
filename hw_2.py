"""
========================================
ПРЕДУПРЕЖДЕНИЕ
========================================

Код для парсинга комментариев использует webdriver, т.к. requests
не умеет работать с js. Комментарии как раз по js и подгружаются.

Далее инструкция под Mac, как начать работать с webdriver.Chrome().
Для Linux и Windows аналогичные действия можно найтив интернете.

Чтобы заработал webdriver.Chrome(),
необходимо его установить использую команду в теминале:
'brew install chromedriver'

Так же используется библиотека selenium, для ее использования
необходимо установить ее в окружение
'ip install selenium'

webdriver.Chrome() может не запускаться, т.к. по умолчанию путь до него
не прописан в PATH. В этом случае, либо прописать путь в PATH, либо явно
указать путь при вызове webdriver.Chrome(). Этим обычно грешит Windows.
"""

import time
import typing
import requests
import bs4

from urllib.parse import urljoin
from pymongo import MongoClient
from selenium import webdriver


class GbBlogParse:
    def __init__(self, base_url: str, start_url: str, collection_mongo):
        self.base_url = base_url
        self.time = time.time()
        self.start_url = start_url
        self.collection = collection_mongo
        self.done_urls = set()
        self.tasks = []
        start_task = self.get_task(self.start_url, self.parse_feed)
        self.tasks.append(start_task)
        self.done_urls.add(self.start_url)

    def _get_response(self, url, *args, **kwargs):
        if self.time + 0.9 < time.time():
            time.sleep(0.5)
        response = requests.get(url, *args, **kwargs)
        self.time = time.time()
        print(url)
        return response

    def _get_soup(self, url, *args, **kwargs):
        soup = bs4.BeautifulSoup(self._get_response(url, *args, **kwargs).text, "lxml")
        return soup

    def get_task(self, url: str, callback: typing.Callable) -> typing.Callable:
        def task():
            soup = self._get_soup(url)
            return callback(url, soup)

        if url in self.done_urls:
            return lambda *_, **__: None
        self.done_urls.add(url)
        return task

    def task_creator(self, url, tags_list, callback):
        links = set(
            urljoin(url, itm.attrs.get("href")) for itm in tags_list if itm.attrs.get("href")
        )
        for link in links:
            task = self.get_task(link, callback)
            self.tasks.append(task)

    def parse_feed(self, url, soup):
        ul_pagination = soup.find("ul", attrs={"class": "gb__pagination"})
        self.task_creator(url, ul_pagination.find_all("a"), self.parse_feed)
        post_wrapper = soup.find("div", attrs={"class": "post-items-wrapper"})
        self.task_creator(
            url, post_wrapper.find_all("a", attrs={"class": "post-item__title"}), self.parse_post
        )

    def parse_post(self, url, soup):
        # Заголовок статьи
        title_tag = (
            soup.find("h1", attrs={"class": "blogpost-title"})
            if soup.find("h1", attrs={"class": "blogpost-title"})
            else ""
        )

        # Обложка. Или же аналог первого исзображения
        cover = (
            soup.find("div", attrs={"class": "hidden", "itemprop": "image"})
            if soup.find("div", attrs={"class": "hidden", "itemprop": "image"})
            else ""
        )

        # Возьмем текст статьи, чтобы искать в нем первую картинку
        if soup.find("div", attrs={"class": "blogpost-content", "itemprop": "articleBody"}):
            post_content = soup.find(
                "div", attrs={"class": "blogpost-content", "itemprop": "articleBody"}
            )
            first_image = (
                post_content.find("img", src=True)["src"]
                if post_content.find("img", src=True)
                else ""
            )
        else:
            first_image = ""

        # Дата публикации
        publication_date = (
            soup.find("time", attrs={"itemprop": "datePublished"})["datetime"]
            if soup.find("time", attrs={"itemprop": "datePublished"})
            else ""
        )

        # Имя автора статьи
        post_author = (
            soup.find("div", attrs={"itemprop": "author"})
            if soup.find("div", attrs={"itemprop": "author"})
            else ""
        )

        # Ссылка на страницу автора
        author_link = (
            urljoin(self.base_url, post_author.find_parent("a", href=True)["href"])
            if post_author.find_parent("a", href=True)
            else ""
        )

        # Количество комментариев
        comments_count = (
            soup.find("comments")["total-comments-count"] if soup.find("comments") else 0
        )

        # Парсинг комментариев сделан через webdriver.Chrome(), что очень замедляет работу.
        # Поэтому лучше не открывать его лишний раз
        comments = self.parse_comments_driver(url) if comments_count else None

        data = {
            "url": url,
            "title": title_tag.text,
            "cover": cover.text,
            "first_image": first_image,
            "publication_date": publication_date,
            "author_link": author_link,
            "comments": comments,
        }
        return data

    def parse_comments_driver(self, url):
        """
        Будем парсить комментарии через отдельное подключение через webdriver.
        T.к. комментарии подгружаются по скрипту,
        то в response для request эти комментарии не попадают. Чтобы скрипты прогрузились,
        будем открывать статью в браузере и брать ее исходный код, а затем уже
        обрабатиывать через BeautifulSoup.
        """

        #  выходной список комментариев
        comments_list_out = []

        # Опции для хрома
        chrome_options = webdriver.ChromeOptions()
        # свойство, чтобы не грузились картинки для ускорения загрузки
        properties = {"profile.managed_default_content_settings.images": 2}
        # Установим свойства
        chrome_options.add_experimental_option("prefs", properties)
        # Опция, чтобы браузер открывался в фоне
        chrome_options.add_argument("--headless")
        # откроем браузер с опциями
        browser = webdriver.Chrome(options=chrome_options)
        # Перейдем по нужной ссылке
        browser.get(url)
        # Получим исходный код страницы
        source_data = browser.page_source
        # Закроем браузер, иначе система забьется открытыми окнами
        browser.close()

        soup = bs4.BeautifulSoup(source_data, "lxml")

        # Найдем все комментарии на странице
        comments_list = soup.find_all("div", attrs={"class": "gb__comment-item-body"})

        # Создадим переменную для списка всех комментариев и заполним данные
        comment_id_list = []
        for itm in comments_list:
            comment_id_list.append(itm["data-comment-id"])

        """Далее идет сама обработка комментария
        На базе словаря family хотел собрать древовидную структуру, но не реализовал.
        При жедании можно из словаря построить дерево и записать комментарии во вложенной структуре
        В текущей реализации пошел немного проще, т.к. не хватило времени, но для каждого комментаря
        записал его родителя, т.к. из этих данных так же можно построить иерархию."""

        family = {}
        # пройдем по найденному списку и соберем данные по комментариям
        for itm in comment_id_list:
            # Надем тэг, где фигурирует id комментария
            tag = soup.find("div", attrs={"data-comment-id": itm})
            # Найдем первого родителя с тэгом li
            parent_tag = tag.find_parent("li")
            # Если родитель найден, то возьмем идентификатор родителя. Он будет в формате comment-xxxxxx
            parent_id = (
                parent_tag.find_parent("li", attrs={"class": "gb__comment-item"})["id"]
                if parent_tag.find_parent("li", attrs={"class": "gb__comment-item"})
                else None
            )

            # Преобразуем найденный идентификатор к нормальному виду или запишем, что его нет
            if parent_id:
                parent_id = parent_id.split(sep="-")[1]
                family.update({itm: parent_id})
            else:
                family.update({itm: None})

            # Заполним идентификатор комментария
            comment_id = itm
            # Заполним идентификатор родителя
            comment_parent_id = parent_id
            # Найдем и заполним текст комментария
            comment_text = (
                soup.find("div", attrs={"data-comment-id": itm}).find_next("p").text.strip()
            )
            # Найдем и заполним дату комментария
            comment_date = (
                soup.find("div", attrs={"data-comment-id": itm})
                .find_previous("span", attrs={"class": "comment-date"})
                .text
            )
            # Найдем и заполним автора комментария
            comment_author = soup.find("div", attrs={"data-comment-id": itm}).find_previous(
                "a", attrs={"class": "gb__comment-item-header-user-data-name"}
            )["creator"]

            # Найдем, сформируем и заполним сылку на автора комментария
            comment_author_link = (
                urljoin(
                    self.base_url,
                    soup.find("div", attrs={"data-comment-id": itm}).find_previous(
                        "a", attrs={"class": "gb__comment-item-header-user-data-name"}
                    )["ng-href"],
                )
                if soup.find("div", attrs={"data-comment-id": itm}).find_previous(
                    "a", attrs={"class": "gb__comment-item-header-user-data-name"}
                )
                else ""
            )

            # Сформируем структуру комментария и сложим все в список
            comment: dict = {
                "comment_id": comment_id,
                "comment_parent_id": comment_parent_id,
                "comment_text": comment_text,
                "comment_date": comment_date,
                "comment_author": comment_author,
                "comment_author_link": comment_author_link,
            }
            comments_list_out.append(comment)

        return comments_list_out

    def run(self):
        for task in self.tasks:
            task_result = task()
            if isinstance(task_result, dict):
                self.save(task_result)

    def save(self, data):
        self.collection.insert_one(data)


if __name__ == "__main__":
    collection = MongoClient()["gb_parse_20_04"]["gb_blog"]
    parser = GbBlogParse("https://gb.ru", "https://gb.ru/posts", collection)
    parser.run()
