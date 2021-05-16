# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy import Request
from scrapy.pipelines.images import ImagesPipeline
from .settings import BOT_NAME
from pymongo import MongoClient


class InstaParsePipeline:
    def process_item(self, item, spider):
        return item


class InstaMongoPipeline:
    def __init__(self):
        client = MongoClient()
        self.db = client[BOT_NAME]

    def process_item(self, item, spider):
        self.db[spider.name + '_' + type(item).__name__].insert_one(ItemAdapter(item).asdict())
        return item


class InstaImageDownloadPipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        for src in item['data']['photo']:
            yield Request(src)

    def item_completed(self, results, item, info):
        if item['data']['photo']:
            item["data"]["photo"] = [itm[1] for itm in results]
        return item
