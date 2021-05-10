import scrapy
import re
import pymongo
from ..loaders import HhLoader, HhLoaderCompany


class HhSpider(scrapy.Spider):
    name = "hh"
    allowed_domains = ["hh.ru"]
    start_urls = ["https://hh.ru/search/vacancy?schedule=remote&L_profession_id=0&area=113"]

    _xpath_selectors = {
        "pagination": '//div[@data-qa="pager-block"]' '//a[@data-qa="pager-page"]/@href',
        "vacancy": '//div[@class="vacancy-serp"]'
        '/div[contains(@class, "vacancy-serp-item ")]'
        '//a[@data-qa="vacancy-serp__vacancy-title"]/@href',
        "author_link": '//a[@data-qa="vacancy-serp__vacancy-employer"]/@href',
    }

    _xpath_data_selectors = {
        "title": '//div[@class="vacancy-title"]' '/h1[@data-qa="vacancy-title"]/text()',
        "salary": '//script[@type="application/ld+json"]/text()',
        "description": '//script[@type="application/ld+json"]/text()',
        "tags": '//div[@class="bloko-tag-list"]' '//span[@data-qa="bloko-tag__text"]/text()',
        "author_link": '//a[@data-qa="vacancy-company-name"]/@href',
    }

    _xpath_author_selectors = {
        "title": '//div[@class="company-header"]'
        '//span[@data-qa="company-header-title-name"]//text()',
        "title_premium": '//h3[@class="b-subtitle b-employerpage-vacancies-title"]',
        "site": '//a[@data-qa="sidebar-company-site"]/@href',
        "sphere": '//div[@class="employer-sidebar-block"]//p/text()',
        "description": '//div[@data-qa="company-description-text"]//text()',
        "description_premium": '//div[contains(@class, "tmpl_hh")]//text()',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_client = pymongo.MongoClient()

    def _get_follow(self, response, selector_str, callback):
        for itm in response.xpath(selector_str):
            yield response.follow(itm, callback=callback)

    def parse(self, response, *args, **kwargs):
        yield from self._get_follow(response, self._xpath_selectors["pagination"], self.parse)

        yield from self._get_follow(
            response, self._xpath_selectors["vacancy"], self.vacancy_parse,
        )

        yield from self._get_follow(
            response, self._xpath_selectors["author_link"], self.author_parse,
        )

    def vacancy_parse(self, response):
        loader = HhLoader(response=response)
        loader.add_value("url", response.url)
        for key, xpath in self._xpath_data_selectors.items():
            loader.add_xpath(key, xpath)

        yield loader.load_item()

    def author_parse(self, response):
        loader = HhLoaderCompany(response=response)
        loader.add_value("url", response.url)
        for key, xpath in self._xpath_author_selectors.items():
            loader.add_xpath(key, xpath)
        yield loader.load_item()
