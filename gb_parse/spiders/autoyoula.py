import re
import scrapy
from pymongo import MongoClient
import base64 as bs64
from urllib.parse import unquote
from gb_parse import settings


class AutoyoulaSpider(scrapy.Spider):
    name = "autoyoula"
    allowed_domains = ["auto.youla.ru"]
    start_urls = ["https://auto.youla.ru/"]

    collection = MongoClient()[settings.MONGODB_DB][settings.MONGODB_COLLECTION]

    def _get_follow(self, response, selector_str, callback):
        for itm in response.css(selector_str):
            url = itm.attrib["href"]
            yield response.follow(url, callback=callback)

    def parse(self, response, *args, **kwargs):
        yield from self._get_follow(
            response,
            ".TransportMainFilters_brandsList__2tIkv .ColumnItemList_column__5gjdt a.blackLink",
            self.brand_parse,
        )

    def brand_parse(self, response):
        yield from self._get_follow(
            response, ".Paginator_block__2XAPy a.Paginator_button__u1e7D", self.brand_parse
        )
        yield from self._get_follow(
            response,
            "article.SerpSnippet_snippet__3O1t2 a.SerpSnippet_name__3F7Yu.blackLink",
            self.car_parse,
        )

    def get_car_feature(self, response):
        feature_list = []
        feature_name_list = response.css(".AdvertSpecs_label__2JHnS::text").extract()
        # Чтобы взять текст из вложенных тэгов можно указать имя класса и
        # через пробел ::text
        feature_value_list = response.css(".AdvertSpecs_data__xK2Qx ::text").extract()
        for i in range(len(feature_name_list)):
            feature_list.append({feature_name_list[i]: feature_value_list[i]})

        return feature_list

    def base64_decode(self, base64_string):
        return bs64.b64decode(base64_string).decode("utf-8")

    def get_author_data(self, response):
        marker = "window.transitState = decodeURIComponent"
        author_data = {}
        for script in response.css("script"):
            try:
                if marker in script.css("::text").extract_first():
                    author_id_pattern = re.compile(
                        r"youlaId%22%2C%22([a-zA-Z|\d]+)%22%2C%22avatar"
                    )
                    author_phone_pattern = re.compile(r"phone%22%2C%22(.*)%22%2C%22time")
                    author_id = re.findall(author_id_pattern, script.css("::text").extract_first())
                    author_phone = re.findall(
                        author_phone_pattern, script.css("::text").extract_first()
                    )
                    if author_phone[0]:
                        author_phone = unquote(author_phone[0])
                        step = 0
                        # 10 попыток декодировать телефон
                        while author_phone[:2] != "+7" and step < 10:
                            author_phone = self.base64_decode(author_phone)
                            step += 1
                    else:
                        author_phone = None

                    author_data.update(
                        {
                            "link": response.urljoin(f"/user/{author_id[0]}").replace(
                                "auto.", "", 1
                            ),
                            "phone": int("".join(filter(lambda d: str.isdigit(d), author_phone))),
                        }
                    )

                    return author_data
            except TypeError as e:
                print(e)
                continue

    def car_parse(self, response):
        print(1)
        feature_list = self.get_car_feature(response)

        data = {
            "url": response.url,
            "title": response.css(".AdvertCard_advertTitle__1S1Ak::text").extract_first(),
            "feature": feature_list,
            "description": response.css(
                ".AdvertCard_descriptionInner__KnuRi::text"
            ).extract_first(),
            "img_list": [
                img.attrib["src"] for img in response.css(".PhotoGallery_photoImage__2mHGn")
            ],
            "author": self.get_author_data(response),
        }
        self.collection.insert_one(data)
