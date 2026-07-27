from __future__ import annotations

from datetime import date as date_

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
    frames: Mapped[list["EpicFrameModel"]] = relationship(
        back_populates="epic_day",
        order_by="EpicFrameModel.position",
        cascade="all, delete-orphan",
    )


class EpicFrameModel(Base):
    __tablename__ = "epic_frame"
    __table_args__ = (UniqueConstraint("epic_day_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    epic_day_id: Mapped[int] = mapped_column(ForeignKey("epic_day.id"))
    telegram_file_id: Mapped[str] = mapped_column(String(256))
    position: Mapped[int]

    epic_day: Mapped[EpicDayModel] = relationship(back_populates="frames")


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    apod_subscribed: Mapped[bool] = mapped_column(default=False)
    epic_subscribed: Mapped[bool] = mapped_column(default=False)
