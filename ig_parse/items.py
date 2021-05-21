# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class IgParseItem(scrapy.Item):
    user_id = scrapy.Field()
    user_name = scrapy.Field()
    meta = scrapy.Field()
    followers = scrapy.Field()
    following = scrapy.Field()
    friends = scrapy.Field()

    @classmethod
    def get_follow_friends(cls, following, followers):
        _following_list = []
        _follower_list = []

        for itm in following:
            _following_list.append(itm['node']['username'])

        for itm in followers:
            _follower_list.append(itm['node']['username'])

        friends = list(set(_following_list) & set(_follower_list))
        return friends
