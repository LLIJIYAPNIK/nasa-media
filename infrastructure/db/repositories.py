from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import InstrumentedAttribute

from domain.digest.entities import DigestEntry
from domain.media.entities import ApodEntry, EpicDay
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User
from infrastructure.db.models import ApodModel, DigestModel, EpicDayModel, UserModel

_SUBSCRIPTION_COLUMNS: dict[MediaSourceKind, InstrumentedAttribute[bool]] = {
    MediaSourceKind.APOD: UserModel.apod_subscribed,
    MediaSourceKind.EPIC: UserModel.epic_subscribed,
    MediaSourceKind.DIGEST: UserModel.digest_subscribed,
}


class _SqlAlchemyRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory


class SqlAlchemyApodRepository(_SqlAlchemyRepository):
    async def get_by_date(self, day: date_) -> ApodEntry | None:
        async with self._session_factory() as session:
            model = await session.scalar(select(ApodModel).where(ApodModel.date == day))
            return ApodEntry(date=model.date, message_id=model.message_id) if model else None

    async def save(self, entry: ApodEntry) -> None:
        async with self._session_factory() as session:
            session.add(ApodModel(date=entry.date, message_id=entry.message_id))
            await session.commit()


class SqlAlchemyEpicRepository(_SqlAlchemyRepository):
    async def get_by_date(self, day: date_) -> EpicDay | None:
        async with self._session_factory() as session:
            model = await self._get_model(session, day)
            return EpicDay(date=model.date, gif_message_id=model.gif_message_id) if model else None

    async def save(self, day: EpicDay) -> None:
        async with self._session_factory() as session:
            model = await self._get_model(session, day.date)
            if model is None:
                model = EpicDayModel(date=day.date)
                session.add(model)
            model.gif_message_id = day.gif_message_id
            await session.commit()

    async def ensure_known_dates(self, days: Sequence[date_]) -> None:
        if not days:
            return
        async with self._session_factory() as session:
            existing = await session.scalars(select(EpicDayModel.date).where(EpicDayModel.date.in_(days)))
            existing_dates = set(existing)
            new_dates = [day for day in days if day not in existing_dates]
            session.add_all(EpicDayModel(date=day) for day in new_dates)
            await session.commit()

    @staticmethod
    async def _get_model(session: AsyncSession, day: date_) -> EpicDayModel | None:
        return await session.scalar(select(EpicDayModel).where(EpicDayModel.date == day))


class SqlAlchemyDigestRepository(_SqlAlchemyRepository):
    async def get_by_date(self, day: date_) -> DigestEntry | None:
        async with self._session_factory() as session:
            model = await session.scalar(select(DigestModel).where(DigestModel.date == day))
            return DigestEntry(date=model.date, message_id=model.message_id) if model else None

    async def save(self, entry: DigestEntry) -> None:
        async with self._session_factory() as session:
            session.add(DigestModel(date=entry.date, message_id=entry.message_id))
            await session.commit()


class SqlAlchemyUserRepository(_SqlAlchemyRepository):
    async def get_by_chat_id(self, chat_id: int) -> User | None:
        async with self._session_factory() as session:
            model = await session.scalar(select(UserModel).where(UserModel.chat_id == chat_id))
            return self._to_domain(model) if model else None

    async def add(self, chat_id: int) -> User:
        async with self._session_factory() as session:
            model = UserModel(chat_id=chat_id)
            session.add(model)
            await session.commit()
            return self._to_domain(model)

    async def save(self, user: User) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(UserModel)
                .where(UserModel.chat_id == user.chat_id)
                .values(
                    apod_subscribed=user.apod_subscribed,
                    epic_subscribed=user.epic_subscribed,
                    digest_subscribed=user.digest_subscribed,
                    birthday=user.birthday,
                )
            )
            await session.commit()

    async def list_subscribed(self, source: MediaSourceKind) -> Sequence[User]:
        column = _SUBSCRIPTION_COLUMNS[source]
        async with self._session_factory() as session:
            models = await session.scalars(select(UserModel).where(column.is_(True)))
            return [self._to_domain(model) for model in models]

    async def list_with_birthday_set(self) -> Sequence[User]:
        async with self._session_factory() as session:
            models = await session.scalars(select(UserModel).where(UserModel.birthday.is_not(None)))
            return [self._to_domain(model) for model in models]

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            chat_id=model.chat_id,
            apod_subscribed=model.apod_subscribed,
            epic_subscribed=model.epic_subscribed,
            digest_subscribed=model.digest_subscribed,
            birthday=model.birthday,
        )
