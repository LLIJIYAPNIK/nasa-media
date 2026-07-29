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
    file_id: Mapped[str | None] = mapped_column(default=None)


class EpicDayModel(Base):
    __tablename__ = "epic_day"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date_] = mapped_column(Date, unique=True)
    gif_message_id: Mapped[int | None] = mapped_column(unique=True, default=None)
    file_id: Mapped[str | None] = mapped_column(default=None)


class DigestModel(Base):
    __tablename__ = "daily_digest"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date_] = mapped_column(Date, unique=True)
    message_id: Mapped[int] = mapped_column(unique=True)
    file_id: Mapped[str | None] = mapped_column(default=None)


class WeeklyHighlightModel(Base):
    __tablename__ = "weekly_highlight"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    week_start_date: Mapped[date_] = mapped_column(Date, unique=True)
    message_id: Mapped[int] = mapped_column(unique=True)
    file_id: Mapped[str | None] = mapped_column(default=None)


class ApodWebEntryModel(Base):
    """Кеш содержимого APOD для веб-сетки (docs/tz/TZ-web-apod.md) — «эти
    данные уже получены от NASA», отдельно от Telegram-кеша ApodModel («это
    сообщение уже переслано в Telegram»)."""

    __tablename__ = "apod_web_entry"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date_] = mapped_column(Date, unique=True)
    title: Mapped[str]
    explanation: Mapped[str]
    copyright: Mapped[str | None] = mapped_column(default=None)
    image_url: Mapped[str]
    hdurl: Mapped[str | None] = mapped_column(default=None)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    apod_subscribed: Mapped[bool] = mapped_column(default=False)
    epic_subscribed: Mapped[bool] = mapped_column(default=False)
    digest_subscribed: Mapped[bool] = mapped_column(default=False)
    weekly_highlights_subscribed: Mapped[bool] = mapped_column(default=False)
    birthday: Mapped[date_ | None] = mapped_column(Date, default=None)
