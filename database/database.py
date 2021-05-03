import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

from . import models


class Database:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)
        models.Base.metadata.create_all(bind=self.engine)
        self.maker = sessionmaker(bind=self.engine)
        self.comments_list = []

    # Вынес проверку на существование в отдельный метод, т.к. в первичной реалихации
    # часто им пользовался.
    def is_exit(self, session, model, query_filter: dict):
        instance = session.query(model).filter_by(**query_filter).first()
        return instance

    # Метод, фактически добавления сущности в сессиию. Сделал предварительное добавление
    # потому что при прохождению по спискам, если не добавить сущность в сессию, то
    # она повторно запишется в базу, например, автор комментария. Ниже будет упоминание
    # об этой проблеме.
    def get_or_create(self, session, model, data, query_filter: dict):
        instance = self.is_exit(session, model, query_filter)
        if not instance:
            instance = model(**data)
            session.add(instance)

        return instance

    # Добавление автора в сессию
    def add_author(self, session, data):
        author = self.get_or_create(
            session, models.Author, data["author_data"], {"url": data["author_data"]["url"]}
        )
        return author

    # Метод для преобразования вложенных списков комментариев
    # в обычный плоский список.
    def comments_tree_to_list(self, data):
        for itm in data:
            if len(itm["comment"]["children"]):
                self.comments_list.append(itm["comment"])
                self.comments_tree_to_list(itm["comment"]["children"])
            else:
                self.comments_list.append(itm["comment"])

    # метод формаирования списка комментариев для привязки к посту с одновременным
    # добавлением в сессию для исключения повторов
    def add_comments(self, session, data):
        comments_out_list = []

        # Выпрямим дерево комментариев
        self.comments_list = []
        self.comments_tree_to_list(data["comments_data"])

        for itm in self.comments_list:
            # Здесь нарвался на неприятность, что мы пытаемся искать автора из сессии,
            # будь то она записанная или нет. Но проблема в том, что на этом этапе комментарий не записан,
            # и значит не записаны и сведения об авторе, а значит для комментариев мы всегда будем перезаписывать
            # пользователя. Чтобы этого не было, сначала запишем пользователя,
            # а затем вернем его в переменную author из метода add_author
            author = self.add_author(
                session,
                {"author_data": {"name": itm["user"]["full_name"], "url": itm["user"]["url"]}},
            )

            # До конца не понял, как отсекать поля, которых нет в модели при записи
            # поэтому вручную прохожу по ключам и оставляю только те, что есть в модели.
            # Если есть идеи, в комментах можно написать как это сделать.
            itm2: dict = {}
            for key in itm.keys():
                if key in ["likes_count", "body", "parent_id", "created_at", "hidden", "deep"]:
                    # преведем текстовый формат к дате для поля created_at
                    if key == "created_at":
                        itm2.update({key: datetime.datetime.fromisoformat(itm[key])})
                    else:
                        itm2.update({key: itm[key]})

            comment = self.get_or_create(
                session,
                models.Comment,
                itm2,
                {"body": itm2["body"], "created_at": itm2["created_at"]},
            )
            # Сделаем отсылку на автора
            comment.author = author
            comments_out_list.append(comment)

        return comments_out_list

    def add_tag(self, session, data):  # model, filter_field, **data):
        tags_list = []
        for itm in data["tags_data"]:
            tags_list.append(self.get_or_create(session, models.Tag, itm, {"name": itm["name"]}))
        return tags_list

    def run_add(self, data):
        session = self.maker()
        post = self.is_exit(session, models.Post, {"url": data["post_data"]["url"]})
        if not post:
            post = models.Post(**data["post_data"])
            comments = self.add_comments(session, data)
            author = self.add_author(session, data)
            tags = self.add_tag(session, data)
            post.author = author
            post.comments.extend(comments)
            post.tags.extend(tags)
            try:
                session.add(post)
                session.commit()
                print("Done")
            except sqlalchemy.exc.IntegrityError:
                session.rollback()
                print("Fail")
            finally:
                session.close()
        else:
            print("Skip")
