# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class InstaTagItem(scrapy.Item):
    date_parse = scrapy.Field()
    data = scrapy.Field()


class InstaPostItem(scrapy.Item):
    date_parse = scrapy.Field()
    data = scrapy.Field()
