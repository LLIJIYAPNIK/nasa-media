from __future__ import annotations

from datetime import date as date_

from sqlalchemy import Date
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ApodModel(Base):
    __tablename__ = "apod"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date_] = mapped_column(Date, unique=True)
    message_id: Mapped[int] = mapped_column(unique=True)


class EpicDayModel(Base):
    __tablename__ = "epic_day"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date_] = mapped_column(Date, unique=True)
    gif_message_id: Mapped[int | None] = mapped_column(unique=True, default=None)


class DigestModel(Base):
    __tablename__ = "daily_digest"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date_] = mapped_column(Date, unique=True)
    message_id: Mapped[int] = mapped_column(unique=True)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    apod_subscribed: Mapped[bool] = mapped_column(default=False)
    epic_subscribed: Mapped[bool] = mapped_column(default=False)
    digest_subscribed: Mapped[bool] = mapped_column(default=False)
    birthday: Mapped[date_ | None] = mapped_column(Date, default=None)
