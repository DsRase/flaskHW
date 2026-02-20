from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer
from os import getenv

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, primary_key=True)
    username: Mapped[str]
    description: Mapped[Optional[str]]

DB_URL = f"postgresql+psycopg2://{getenv("DB_USER")}:{getenv("DB_PASS")}@{getenv("DB_HOST")}:5432/{getenv("DB_NAME")}"
engine = create_engine(DB_URL)

Base.metadata.create_all(engine)