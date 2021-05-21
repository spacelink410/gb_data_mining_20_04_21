from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, Compose


class IgUserLoaders(ItemLoader):
    default_item_class = dict

    user_id_out = TakeFirst()
    user_name_out = TakeFirst()
