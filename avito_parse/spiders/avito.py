import scrapy
import pymongo
from ..loaders import AvitoLoader
from ..xpath_expr import xpath_link_selectors, xpath_model_selectors


class AvitoSpider(scrapy.Spider):
    name = 'avito'
    allowed_domains = ['avito.ru']
    start_urls = ['https://www.avito.ru/habarovsk/nedvizhimost']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_client = pymongo.MongoClient()

    def _get_follow(self, response, selector_str, callback):
        for itm in response.xpath(selector_str):
            yield response.follow(itm, callback=callback)

    def parse(self, response, *args, **kwargs):

        yield from self._get_follow(
            response, xpath_link_selectors["category"], self.parse
        )

        yield from self._get_follow(
            response, xpath_link_selectors["pagination"], self.parse
        )

        yield from self._get_follow(
            response, xpath_link_selectors["advert"], self.advert_item_parse,
        )

    def advert_item_parse(self, response):
        loader = AvitoLoader(response=response)
        loader.add_value('url', response.url)
        for key, xpath in xpath_model_selectors.items():
            loader.add_xpath(key, xpath)

        yield loader.load_item()
