from datetime import date

from domain.digest.entities import DigestEntry, WeeklyHighlightEntry
from domain.media.entities import ApodEntry, ApodWebEntry, EpicDay
from domain.media.value_objects import MediaSourceKind
from infrastructure.db.repositories import (
    SqlAlchemyApodRepository,
    SqlAlchemyApodWebCacheRepository,
    SqlAlchemyDigestRepository,
    SqlAlchemyEpicRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyWeeklyHighlightsRepository,
)


async def test_apod_repository_roundtrip(session_factory):
    repo = SqlAlchemyApodRepository(session_factory)
    day = date(2024, 1, 1)

    assert await repo.get_by_date(day) is None

    await repo.save(ApodEntry(date=day, message_id=10))

    assert await repo.get_by_date(day) == ApodEntry(date=day, message_id=10)


async def test_apod_repository_file_id_roundtrip(session_factory):
    repo = SqlAlchemyApodRepository(session_factory)
    day = date(2024, 1, 1)

    await repo.save(ApodEntry(date=day, message_id=10, file_id="apod-file-10"))

    entry = await repo.get_by_date(day)
    assert entry is not None
    assert entry.file_id == "apod-file-10"


async def test_apod_web_cache_repository_get_by_dates_empty_table(session_factory):
    repo = SqlAlchemyApodWebCacheRepository(session_factory)

    assert await repo.get_by_dates([date(2024, 1, 1)]) == {}


async def test_apod_web_cache_repository_save_many_and_get_by_dates_roundtrip(session_factory):
    repo = SqlAlchemyApodWebCacheRepository(session_factory)
    first = ApodWebEntry(
        date=date(2024, 1, 1),
        title="Title1",
        explanation="Text1",
        copyright=None,
        image_url="http://img1",
        hdurl=None,
    )
    second = ApodWebEntry(
        date=date(2024, 1, 2),
        title="Title2",
        explanation="Text2",
        copyright="Jane",
        image_url="http://img2",
        hdurl="http://img2-hd",
    )

    await repo.save_many([first, second])

    result = await repo.get_by_dates([date(2024, 1, 1), date(2024, 1, 2)])
    assert result == {date(2024, 1, 1): first, date(2024, 1, 2): second}


async def test_apod_web_cache_repository_get_by_dates_returns_only_found(session_factory):
    repo = SqlAlchemyApodWebCacheRepository(session_factory)
    entry = ApodWebEntry(
        date=date(2024, 1, 1),
        title="Title1",
        explanation="Text1",
        copyright=None,
        image_url="http://img1",
        hdurl=None,
    )
    await repo.save_many([entry])

    result = await repo.get_by_dates([date(2024, 1, 1), date(2024, 1, 2)])

    assert result == {date(2024, 1, 1): entry}


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


async def test_epic_repository_file_id_roundtrip(session_factory):
    repo = SqlAlchemyEpicRepository(session_factory)
    day = date(2024, 1, 1)
    await repo.ensure_known_dates([day])

    await repo.save(EpicDay(date=day, gif_message_id=123, file_id="epic-gif-123"))

    epic_day = await repo.get_by_date(day)
    assert epic_day is not None
    assert epic_day.file_id == "epic-gif-123"


async def test_digest_repository_roundtrip(session_factory):
    repo = SqlAlchemyDigestRepository(session_factory)
    day = date(2024, 1, 1)

    assert await repo.get_by_date(day) is None

    await repo.save(DigestEntry(date=day, message_id=10))

    assert await repo.get_by_date(day) == DigestEntry(date=day, message_id=10)


async def test_digest_repository_file_id_roundtrip(session_factory):
    repo = SqlAlchemyDigestRepository(session_factory)
    day = date(2024, 1, 1)

    await repo.save(DigestEntry(date=day, message_id=10, file_id="digest-file-10"))

    entry = await repo.get_by_date(day)
    assert entry is not None
    assert entry.file_id == "digest-file-10"


async def test_weekly_highlights_repository_roundtrip(session_factory):
    repo = SqlAlchemyWeeklyHighlightsRepository(session_factory)
    week_start_date = date(2026, 7, 27)

    assert await repo.get_by_date(week_start_date) is None

    await repo.save(WeeklyHighlightEntry(week_start_date=week_start_date, message_id=10))

    assert await repo.get_by_date(week_start_date) == WeeklyHighlightEntry(
        week_start_date=week_start_date, message_id=10
    )


async def test_weekly_highlights_repository_file_id_roundtrip(session_factory):
    repo = SqlAlchemyWeeklyHighlightsRepository(session_factory)
    week_start_date = date(2026, 7, 27)

    await repo.save(WeeklyHighlightEntry(week_start_date=week_start_date, message_id=10, file_id="weekly-file-10"))

    entry = await repo.get_by_date(week_start_date)
    assert entry is not None
    assert entry.file_id == "weekly-file-10"


async def test_user_repository_weekly_highlights_subscription_roundtrip(session_factory):
    repo = SqlAlchemyUserRepository(session_factory)

    user = await repo.add(chat_id=888)
    assert user.weekly_highlights_subscribed is False

    await repo.save(user.with_subscription(MediaSourceKind.WEEKLY_HIGHLIGHTS, True))

    subscribed = await repo.list_subscribed(MediaSourceKind.WEEKLY_HIGHLIGHTS)
    assert [u.chat_id for u in subscribed] == [888]

    fetched = await repo.get_by_chat_id(888)
    assert fetched is not None
    assert fetched.weekly_highlights_subscribed is True


async def test_user_repository_subscription_roundtrip(session_factory):
    repo = SqlAlchemyUserRepository(session_factory)

    user = await repo.add(chat_id=555)
    assert user.apod_subscribed is False

    await repo.save(user.with_subscription(MediaSourceKind.APOD, True))

    subscribed = await repo.list_subscribed(MediaSourceKind.APOD)
    assert [u.chat_id for u in subscribed] == [555]

    unsubscribed = await repo.list_subscribed(MediaSourceKind.EPIC)
    assert unsubscribed == []


async def test_user_repository_digest_subscription_roundtrip(session_factory):
    repo = SqlAlchemyUserRepository(session_factory)

    user = await repo.add(chat_id=777)
    assert user.digest_subscribed is False

    await repo.save(user.with_subscription(MediaSourceKind.DIGEST, True))

    subscribed = await repo.list_subscribed(MediaSourceKind.DIGEST)
    assert [u.chat_id for u in subscribed] == [777]

    fetched = await repo.get_by_chat_id(777)
    assert fetched is not None
    assert fetched.digest_subscribed is True
    assert fetched.apod_subscribed is False
    assert fetched.epic_subscribed is False


async def test_user_repository_birthday_roundtrip_and_listing(session_factory):
    repo = SqlAlchemyUserRepository(session_factory)

    with_birthday = await repo.add(chat_id=1)
    without_birthday = await repo.add(chat_id=2)
    assert with_birthday.birthday is None

    await repo.save(with_birthday.with_birthday(date(1990, 5, 20)))

    fetched = await repo.get_by_chat_id(1)
    assert fetched is not None
    assert fetched.birthday == date(1990, 5, 20)

    with_birthday_set = await repo.list_with_birthday_set()
    assert [u.chat_id for u in with_birthday_set] == [1]
    assert without_birthday.chat_id not in [u.chat_id for u in with_birthday_set]
