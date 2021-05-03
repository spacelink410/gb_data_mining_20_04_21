from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime, Boolean
from .mixins import UrlMixin

Base = declarative_base()

tag_post = Table(
    "tag_post",
    Base.metadata,
    Column("post_id", Integer, ForeignKey("post.id")),
    Column("tag_id", Integer, ForeignKey("tag.id")),
)


class Comment(Base):
    __tablename__ = "comment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    likes_count = Column(Integer)
    body = Column(String)
    parent_id = Column(Integer, ForeignKey("comment.id"))
    created_at = Column(DateTime)
    post_id = Column(Integer, ForeignKey("post.id"))
    post = relationship("Post", backref="comments")
    hidden = Column(Boolean)
    deep = Column(Integer)
    author_id = Column(Integer, ForeignKey("author.id"))
    author = relationship("Author", backref="comments")


class Post(Base, UrlMixin):
    __tablename__ = "post"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(250), nullable=False, unique=False)
    cover = Column(String(200), nullable=True)
    first_image = Column(String(200), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    author_id = Column(Integer, ForeignKey("author.id"), nullable=False)
    author = relationship("Author", backref="posts")
    tags = relationship("Tag", secondary=tag_post)


class Author(Base, UrlMixin):
    __tablename__ = "author"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)


class Tag(Base, UrlMixin):
    __tablename__ = "tag"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    posts = relationship(Post, secondary=tag_post)
