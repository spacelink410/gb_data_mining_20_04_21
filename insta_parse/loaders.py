from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, Compose


def get_tag_data(tag_graphql):
    tag_graphql = tag_graphql[0]
    data_out = {}
    for key, value in tag_graphql.items():
        if not (isinstance(value, dict) or isinstance(value, list)):
            data_out.update({key: value})
    return data_out


def get_post_data(post_graphql):
    post_graphql = post_graphql[0]
    data_out = {}

    data_out.update({
        'id': post_graphql['node']['id'],
        'shortcode': post_graphql['node']['shortcode'],
        'owner': post_graphql['node']['owner']['id'],
        'photo': None if post_graphql['node']['is_video'] else post_graphql['node']['thumbnail_resources'][-1]['src'],
        'meta': post_graphql['node']
    })

    return data_out


class InstaTagLoaders(ItemLoader):
    default_item_class = dict

    data_in = Compose(get_tag_data)

    date_parse_out = TakeFirst()
    data_out = TakeFirst()


class InstaPostLoaders(ItemLoader):
    default_item_class = dict

    data_in = Compose(get_post_data)

    date_parse_out = TakeFirst()
    data_out = TakeFirst()
