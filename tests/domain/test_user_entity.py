from datetime import date

import pytest

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


# --- MediaSourceKind.DIGEST (regression coverage for the dict-based
# is_subscribed/with_subscription refactor — APOD/EPIC must keep working) ---


def test_is_subscribed_reads_digest_field():
    user = User(chat_id=1, digest_subscribed=True)

    assert user.is_subscribed(MediaSourceKind.DIGEST) is True


def test_with_subscription_sets_digest_field():
    user = User(chat_id=1)

    updated = user.with_subscription(MediaSourceKind.DIGEST, True)

    assert user.digest_subscribed is False
    assert updated.digest_subscribed is True


@pytest.mark.parametrize("source", [MediaSourceKind.APOD, MediaSourceKind.EPIC, MediaSourceKind.DIGEST])
def test_with_subscription_only_touches_the_targeted_source(source: MediaSourceKind):
    user = User(chat_id=1, apod_subscribed=True, epic_subscribed=True, digest_subscribed=True)

    updated = user.with_subscription(source, False)

    for other_source in MediaSourceKind:
        expected = False if other_source is source else True
        assert updated.is_subscribed(other_source) is expected
