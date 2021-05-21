import scrapy
import json
from ..items import IgParseItem
from ..loaders import IgUserLoaders
from scrapy.exceptions import DropItem, CloseSpider

# TODO вынести некоторые проверки в DownloaderMiddleware
class IgSpider(scrapy.Spider):
    name = 'ig'
    allowed_domains = ['instagram.com']
    start_urls = ['https://www.instagram.com']

    # Дополнителные переменные
    login_url = 'https://www.instagram.com/accounts/login/ajax/'
    hash_followers = '5aefa9893005572d237da5068082d8d5'  # подписчики
    hash_following = '3dec7e2c57367ef3da3d987d89f9dbc8'  # подписки
    api_url = '/graphql/query/'

    # Заголовки запросов
    header_var = {'include_reel': 'false',
                  'fetch_mutual': 'false',
                  'first': 24}

    def __init__(self, login: str, password: str, ig_users: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login = login
        self.password = password
        self.ig_users = ig_users

    def parse(self, response, **kwargs):
        js_data = self.js_data_extract(response)
        # если из сохраненных cookie подтянулась сессиия, т.е. инста определила нас
        # как viewer, то переходим к парсингу страницы пользователя
        # В настройках прописано так, что cookie хранятся на диске, а не в памяти
        # это сделано для того, чтобы меньше нервировать инсту авторизациями
        if js_data['config']['viewer'] is not None:
            # ставим в очередь каждого пользователя, из входного масссива
            for itm in self.ig_users:
                yield response.follow(f"/{itm}/",
                                      callback=self.parse_user_from_login,
                                      cb_kwargs=dict(is_first_check=True))
        else:  # иначе проходим процедуру авторизации и начинаем сначала
            try:
                yield scrapy.FormRequest(
                    self.login_url,
                    method="POST",
                    callback=self.parse,
                    formdata={"username": self.login, "enc_password": self.password},
                    headers={"X-CSRFToken": js_data["config"]["csrf_token"]},
                )
            except AttributeError:
                pass

    def parse_user_from_login(self, response, is_first_check):
        user_item = IgParseItem()
        user_loader = IgUserLoaders(user_item)

        # Сначала добавить проверку, что аккаункт существует.
        # Далее, если аккаунт не закрытый, то парсим аккаунт
        try:
            js_data = self.js_data_extract(response)
            if not js_data['entry_data']['ProfilePage'][0]['graphql']['user']['is_private']:
                user_id = js_data['entry_data']['ProfilePage'][0]['graphql']['user']['id']
                user_name = js_data['entry_data']['ProfilePage'][0]['graphql']['user']['username']

                self.header_var['id'] = user_id

                user_loader.add_value('user_id', user_id)
                user_loader.add_value('user_name', user_name)
                user_loader.add_value('meta', js_data['entry_data']['ProfilePage'][0]['graphql']['user'])

                # перейдем к парсингу подписок пользователя
                yield response.follow(f"{self.api_url}?"
                                      f"query_hash={self.hash_followers}&"
                                      f"variables={json.dumps(self.header_var)}",
                                      callback=self.parse_followers,
                                      cb_kwargs=dict(item=user_item,
                                                     user_loader=user_loader))
            else:
                if is_first_check:
                    raise CloseSpider("Закрытый аккаунт на входе. Парсинг остановлен")
                else:
                    raise DropItem(f"Закрытый аккаунт")

        except AttributeError:
            if is_first_check:
                raise CloseSpider("Входной аккаунт не существует. Парсинг остановлен")
            else:
                raise DropItem(f"Аккаунт не существует.")

    def parse_followers(self, response, item, user_loader, is_pagination_off=False):
        data = response.json()
        self.header_var['after'] = data['data']['user']['edge_followed_by']['page_info']['end_cursor']
        user_loader.add_value('followers', data['data']['user']['edge_followed_by']['edges'])

        if not data['data']['user']['edge_followed_by']['page_info']['has_next_page']:
            is_pagination_off = True

        if is_pagination_off:  # пагинации нет, то идем к списку подписчиков
            yield response.follow(f"{self.api_url}?"
                                  f"query_hash={self.hash_following}&"
                                  f"variables="f"{json.dumps(self.header_var)}",
                                  callback=self.parse_following,
                                  cb_kwargs=dict(item=item,
                                                 user_loader=user_loader))
        else:  # инчае идем по страницам
            yield response.follow(f"{self.api_url}?"
                                  f"query_hash={self.hash_followers}&"
                                  f"variables="f"{json.dumps(self.header_var)}",
                                  callback=self.parse_followers,
                                  cb_kwargs=dict(item=item,
                                                 user_loader=user_loader,
                                                 is_pagination_off=is_pagination_off))

    def parse_following(self, response, item, user_loader, is_pagination_off=False):
        data = response.json()
        self.header_var['after'] = data['data']['user']['edge_follow']['page_info']['end_cursor']
        user_loader.add_value('following', data['data']['user']['edge_follow']['edges'])

        if not data['data']['user']['edge_follow']['page_info']['has_next_page']:
            is_pagination_off = True

        # если пагинации больше нет
        if is_pagination_off:
            # сформируем перечень друзей - взаимные рукопожатия
            # в случае, если хотябы один из списков будет пустой, то
            # друзей искать бессмысленно и будет ошибка TypeError
            try:
                friends = IgParseItem.get_follow_friends(user_loader._values.get('following'),
                                                         user_loader._values.get('followers'))
                user_loader.add_value('friends', friends)
            except TypeError:
                # проинициализируем список друзей
                friends = []

            # передаем пользователя на след. pipeline
            yield user_loader.load_item()

            # переход к парсингу друзей
            for itm in friends:
                yield response.follow(f"/{itm}/",
                                      callback=self.parse_user_from_login,
                                      cb_kwargs=dict(is_first_check=False))
        else:
            # инчае идем к пагинации для дополнения списка
            yield response.follow(f"{self.api_url}?"
                                  f"query_hash={self.hash_following}&"
                                  f"variables="f"{json.dumps(self.header_var)}",
                                  callback=self.parse_following,
                                  cb_kwargs=dict(item=item,
                                                 user_loader=user_loader,
                                                 is_pagination_off=is_pagination_off))

    def js_data_extract(self, response):
        script = response.xpath(
            "//script[contains(text(), 'window._sharedData =')]/text()"
        ).extract_first()

        return json.loads(script.replace("window._sharedData = ", "")[:-1])

    def parsing_cookie(self, response) -> dict:
        _cookie = response.request.headers.get('Cookie')[0].decode('utf-8').split(';')

        cookie_dict = {}
        for itm in _cookie:
            cookie_d = itm.split('=')
            try:
                cookie_dict.update({cookie_d[0]: cookie_d[1]})
            except IndexError:
                cookie_dict.update({cookie_d[0]: None})

        return cookie_dict
