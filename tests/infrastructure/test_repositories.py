from datetime import date

from domain.media.entities import ApodEntry, EpicDay
from domain.media.value_objects import MediaSourceKind
from infrastructure.db.repositories import SqlAlchemyApodRepository, SqlAlchemyEpicRepository, SqlAlchemyUserRepository


async def test_apod_repository_roundtrip(session_factory):
    repo = SqlAlchemyApodRepository(session_factory)
    day = date(2024, 1, 1)

    assert await repo.get_by_date(day) is None

    await repo.save(ApodEntry(date=day, message_id=10))

    assert await repo.get_by_date(day) == ApodEntry(date=day, message_id=10)


async def test_epic_repository_ensure_known_dates_is_idempotent(session_factory):
    repo = SqlAlchemyEpicRepository(session_factory)
    day = date(2024, 1, 1)

    await repo.ensure_known_dates([day])
    await repo.ensure_known_dates([day])

    epic_day = await repo.get_by_date(day)
    assert epic_day is not None
    assert epic_day.gif_message_id is None
    assert epic_day.is_cached is False


async def test_epic_repository_save_gif_message_id(session_factory):
    repo = SqlAlchemyEpicRepository(session_factory)
    day = date(2024, 1, 1)
    await repo.ensure_known_dates([day])

    await repo.save(EpicDay(date=day, gif_message_id=123))

    epic_day = await repo.get_by_date(day)
    assert epic_day is not None
    assert epic_day.gif_message_id == 123
    assert epic_day.is_cached is True


async def test_user_repository_subscription_roundtrip(session_factory):
    repo = SqlAlchemyUserRepository(session_factory)

    user = await repo.add(chat_id=555)
    assert user.apod_subscribed is False

    await repo.save(user.with_subscription(MediaSourceKind.APOD, True))

    subscribed = await repo.list_subscribed(MediaSourceKind.APOD)
    assert [u.chat_id for u in subscribed] == [555]

    unsubscribed = await repo.list_subscribed(MediaSourceKind.EPIC)
    assert unsubscribed == []
