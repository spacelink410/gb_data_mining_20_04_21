import time
import typing
import requests
import bs4
import datetime

from urllib.parse import urljoin
from selenium import webdriver

from database.database import Database


class GbBlogParse:
    def __init__(self, base_url: str, start_url: str, db):
        self.base_url = base_url
        self.time = time.time()
        self.start_url = start_url
        self.db = db
        self.done_urls = set()
        self.tasks = []
        start_task = self.get_task(self.start_url, self.parse_feed)
        self.tasks.append(start_task)
        self.done_urls.add(self.start_url)

    def _get_response(self, url, *args, **kwargs):
        if self.time + 0.9 < time.time():
            time.sleep(0.5)
        response = requests.get(url, *args, **kwargs)
        self.time = time.time()
        print(url)
        return response

    def _get_soup(self, url, *args, **kwargs):
        soup = bs4.BeautifulSoup(self._get_response(url, *args, **kwargs).text, "lxml")
        return soup

    def get_task(self, url: str, callback: typing.Callable) -> typing.Callable:
        def task():
            soup = self._get_soup(url)
            return callback(url, soup)

        if url in self.done_urls:
            return lambda *_, **__: None
        self.done_urls.add(url)
        return task

    def task_creator(self, url, tags_list, callback):
        links = set(
            urljoin(url, itm.attrs.get("href")) for itm in tags_list if itm.attrs.get("href")
        )
        for link in links:
            task = self.get_task(link, callback)
            self.tasks.append(task)

    def parse_feed(self, url, soup):
        ul_pagination = soup.find("ul", attrs={"class": "gb__pagination"})
        self.task_creator(url, ul_pagination.find_all("a"), self.parse_feed)
        post_wrapper = soup.find("div", attrs={"class": "post-items-wrapper"})
        self.task_creator(
            url, post_wrapper.find_all("a", attrs={"class": "post-item__title"}), self.parse_post
        )

    def parse_post(self, url, soup):
        # Заголовок статьи
        title_tag = (
            soup.find("h1", attrs={"class": "blogpost-title"})
            if soup.find("h1", attrs={"class": "blogpost-title"})
            else ""
        )

        # Обложка. Или же аналог первого исзображения
        cover = (
            soup.find("div", attrs={"class": "hidden", "itemprop": "image"})
            if soup.find("div", attrs={"class": "hidden", "itemprop": "image"})
            else ""
        )

        # Возьмем текст статьи, чтобы искать в нем первую картинку
        if soup.find("div", attrs={"class": "blogpost-content", "itemprop": "articleBody"}):
            post_content = soup.find(
                "div", attrs={"class": "blogpost-content", "itemprop": "articleBody"}
            )
            first_image = (
                post_content.find("img", src=True)["src"]
                if post_content.find("img", src=True)
                else ""
            )
        else:
            first_image = ""

        # Дата публикации
        publication_date = (
            soup.find("time", attrs={"itemprop": "datePublished"})["datetime"]
            if soup.find("time", attrs={"itemprop": "datePublished"})
            else ""
        )
        publication_date = (
            datetime.datetime.fromisoformat(publication_date) if publication_date else None
        )

        # Имя автора статьи
        post_author = (
            soup.find("div", attrs={"itemprop": "author"})
            if soup.find("div", attrs={"itemprop": "author"})
            else ""
        )

        # Ссылка на страницу автора
        author_link = (
            urljoin(self.base_url, post_author.find_parent("a", href=True)["href"])
            if post_author.find_parent("a", href=True)
            else ""
        )

        data = {
            "post_data": {
                "url": url,
                "title": title_tag.text,
                "cover": cover.text,
                "first_image": first_image,
                "publication_date": publication_date,
            },
            "author_data": {"url": author_link, "name": post_author.text,},
            "tags_data": [
                {"name": tag.text, "url": urljoin(url, tag.attrs.get("href"))}
                for tag in soup.find_all("a", attrs={"class": "small"})
            ],
            "comments_data": self._get_comments(soup.find("comments").attrs.get("commentable-id")),
        }

        return data

    def _get_comments(self, post_id):
        api_path = f"/api/v2/comments?commentable_type=Post&commentable_id={post_id}&order=desc"
        response = self._get_response(urljoin(self.start_url, api_path))
        data = response.json()
        return data

    def run(self):
        for task in self.tasks:
            task_result = task()
            if isinstance(task_result, dict):
                self.save(task_result)

    def save(self, data):
        self.db.run_add(data)


if __name__ == "__main__":
    db = Database("sqlite:///gb_blog.db")
    parser = GbBlogParse("https://gb.ru", "https://gb.ru/posts", db)
    parser.run()
