from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose, Compose


def generate_features(features_list: list):
    features = {}

    features_list = list(map(lambda x: str(x).strip(), features_list))
    clear_list = list(filter(lambda x: x != "" and x != "\n", features_list))

    size = len(clear_list)

    for i in range(0, size, 2):
        if i < size - 1:
            features.update({clear_list[i]: clear_list[i + 1]})

    return features


def strip_address(address):
    yield str(address).strip()


class AvitoLoader(ItemLoader):
    default_item_class = dict

    address_in = MapCompose(strip_address)
    features_in = Compose(generate_features)

    url_out = TakeFirst()
    title_out = TakeFirst()
    price_out = TakeFirst()
    address_out = TakeFirst()
    features_out = TakeFirst()
    author_lik_out = TakeFirst()
