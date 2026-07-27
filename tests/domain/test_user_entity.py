from datetime import date

from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User


def test_is_subscribed_reads_correct_field():
    user = User(chat_id=1, apod_subscribed=True, epic_subscribed=False)

    assert user.is_subscribed(MediaSourceKind.APOD) is True
    assert user.is_subscribed(MediaSourceKind.EPIC) is False


def test_with_subscription_returns_new_instance_without_mutating_original():
    user = User(chat_id=1)

    updated = user.with_subscription(MediaSourceKind.EPIC, True)

    assert user.epic_subscribed is False
    assert updated.epic_subscribed is True
    assert updated.chat_id == user.chat_id


def test_with_birthday_returns_new_instance_without_mutating_original():
    user = User(chat_id=1)

    updated = user.with_birthday(date(1990, 5, 20))

    assert user.birthday is None
    assert updated.birthday == date(1990, 5, 20)
