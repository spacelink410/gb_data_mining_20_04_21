# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# useful for handling different item types with a single interface

from itemadapter import ItemAdapter
from .settings import BOT_NAME
from pymongo import MongoClient


class IgParsePipeline:
    def process_item(self, item, spider):
        return item


class IgMongoPipeline:
    def __init__(self):
        client = MongoClient()
        self.db = client[BOT_NAME]

    def process_item(self, item, spider):
        db_coll = spider.name + '_' + type(item).__name__
        # если запись есть, то она обновится,
        # иначе создастся новая
        # сделано, чтобы база накапливалась, а не дублировалась
        self.db[db_coll].update_one({'user_id': item['user_id']},
                                    {"$set": ItemAdapter(item).asdict()},
                                    upsert=True)
        return item


class IgSearchChain:
    def __init__(self):
        client = MongoClient()
        self.db = client[BOT_NAME]

    def process_item(self, item, spider):
        user_list = spider.ig_users
        db_coll = spider.name + '_' + type(item).__name__

        # TODO Найти решение для вывода одного значения в chains средствами базы
        db_pipeline = [
            {"$match": {"user_name": user_list[0]}},
            {"$graphLookup": {'from': db_coll,
                              'startWith': "$friends",
                              'connectFromField': 'friends',
                              'connectToField': 'user_name',
                              'as': 'chains',
                              'depthField': 'numConnections',
                              'restrictSearchWithMatch': {}}}]

        connection_result = list(self.db[db_coll].aggregate(db_pipeline))[0]

        if connection_result:  # если монга обнаружила запись с первым пользователем
            # то проверим, есть ли в цепочках путь до 2 пользователя
            for itm in connection_result['chains']:
                # если запись найдена, значит есть путь от пользователя 1 до пользователя 2
                # , то формируем список и идем в поиcк цепочки
                if user_list[1] == itm['user_name']:
                    spider.crawler.engine.close_spider(self, reason='Найдена цепочка. Дальнейший парсинг остановлен')
                    # Если второй пользователь в списке друзей первого, выведем ветку графа
                    if user_list[1] in connection_result['friends']:
                        with open('out_2', 'w') as out_2:
                            print(f'Пользователь {user_list[0]} является другом {user_list[1]}', file=out_2)
                        return item
                    else:
                        result_chain = self.search_chain(user_list[0],  # передадим первого пользователя
                                                         user_list[1],  # передадим второго пользователя
                                                         # друзей первого пользователя для для дальнейшего определения цепочки
                                                         connection_result['friends'],
                                                         int(itm['numConnections']),
                                                         db_pipeline,
                                                         db_coll)
                        with open('out', 'w') as out:
                            print(result_chain, file=out) if result_chain else print('цепочки не найдены', file=out)
                        return item
                else:
                    print('цепочки не найдены')

    def search_chain(self, user_1, user_2, target_list, num_connections, db_pipeline, db_coll):
        chain_result: dict = {}
        num_connections -= 1

        # список с финальной цепочкой
        chain_result[user_1] = []
        # сохраним ключ узла предыдущей итерации для цепочки
        reverse_user = user_1

        while num_connections > -1:
            target_list_2 = []
            # начинаем обход полученного списка друзей
            for itm in target_list:
                # заменим идентификатор пользователя для запроса агрегации
                db_pipeline[0]['$match']['user_name'] = itm

                # поместим в переменную всю сущность для дальнейшей работы
                itm = self.db[db_coll].find_one({'user_name': itm})

                # для каждого друга делаем запрос аггрегации для поиска цепочем с user_2
                # connection_result = list(db[db_coll].aggregate(db_pipeline))[0]
                # при этом у пользователя может быть друг, которого мы еще не спарсили
                # и его не будет в базе
                try:
                    connection_result = list(self.db[db_coll].aggregate(db_pipeline))[0]
                except IndexError:
                    connection_result = {}
                    connection_result.setdefault('chains', [])

                # выносим цепочку в отдельную переменную
                chains_list = connection_result['chains']
                # проходим по всем позициям цепочки
                for chains_itm in chains_list:
                    # если в цепочке есть позиция с искомым user_2, и число узлов между позицией и
                    # user_2 такое же как на входе, т.е. на 1 меньше, чем в предыдущей итерации

                    if chains_itm['user_name'] == user_2 and chains_itm['numConnections'] == num_connections:
                        # формируем список друзей для следующей итерации из списка друзей
                        # текущего chains_itm
                        chain_result[reverse_user] = [itm['user_name']]
                        # записываем новый узел
                        reverse_user = itm['user_name']

                        if num_connections > 0:
                            target_list_2 = itm['friends']
                            # создадим ключ, если ранее его еще не было
                            chain_result.setdefault(reverse_user, [])
                            # запишем связь в узел
                            chain_result[reverse_user] += [itm['user_name']]
                        else:
                            chain_result.setdefault(reverse_user, [])
                            chain_result[reverse_user] += [chains_itm['user_name']]

            num_connections -= 1
            target_list = target_list_2
        return chain_result
