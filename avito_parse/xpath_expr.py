"""
Селекторы для паука
"""

xpath_link_selectors = {
    'category': '//a[@data-marker="category[1000030]/link"]/@href',
    'pagination': '//a[@class="pagination-page"]/@href',
    'advert': '//div[@data-marker="catalog-serp"]'
              '//div[@data-marker="item"]'
              '//a[@data-marker="item-title"]/@href',
}

xpath_model_selectors = {
    'title': '//div[@class="title-info-main"]//span[@itemprop="name"]/text()',
    'price': '//meta[@property="product:price:amount"]/@content',
    'address': '//div[@class="item-address"]//div[@itemprop="address"]//text()',
    'features': '//div[@class="item-params"]//li[@class="item-params-list-item"]//text()',
    'author_lik': '//div[@data-marker="seller-info/name"]/a/@href'
}
