import json
import re
import urllib.parse as ul
from .settings import BASE_URL
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Join


def get_price(script):
    json_data = json.loads(script)
    try:
        salary = {"currency": json_data["baseSalary"]["currency"]}
        for key, value in json_data["baseSalary"]["value"].items():
            salary.update({key: value})
        salary.pop("@type")

        return salary

    except KeyError:
        return []


def get_description(script):
    json_data = json.loads(script)
    if json_data["description"]:
        yield json_data["description"]
    else:
        yield []


def get_title_premium(title):
    title = re.findall("Вакансии компании «(.*)»", title)
    return title


def join_url_author(url):
    yield ul.urljoin(BASE_URL, url)


class HhLoader(ItemLoader):
    default_item_class = dict

    salary_in = MapCompose(get_price)
    description_in = MapCompose(get_description)
    author_link_in = MapCompose(join_url_author)

    url_out = TakeFirst()
    title_out = TakeFirst()
    salary_out = TakeFirst()
    description_out = TakeFirst()
    author_link_out = TakeFirst()


class HhLoaderCompany(ItemLoader):
    default_item_class = dict

    title_in = Join(separator="")
    title_premium_in = MapCompose(get_title_premium)
    description_in = Join(separator=" ")
    description_premium_in = Join(separator=" ")

    url_out = TakeFirst()
    title_out = TakeFirst()
    title_premium_out = TakeFirst()
    site_out = TakeFirst()
    description_out = TakeFirst()
    description_premium_out = TakeFirst()
