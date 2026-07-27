from application.subscriptions.manage_subscription import SetSubscription
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User
from tests.application.fakes import FakeUserRepository


async def test_set_subscription_updates_and_persists():
    user_repo = FakeUserRepository([User(chat_id=1)])
    use_case = SetSubscription(user_repo)

    updated = await use_case.execute(1, MediaSourceKind.EPIC, True)

    assert updated.epic_subscribed is True
    persisted = await user_repo.get_by_chat_id(1)
    assert persisted.epic_subscribed is True


async def test_set_subscription_does_not_touch_other_source():
    user_repo = FakeUserRepository([User(chat_id=1, apod_subscribed=True)])
    use_case = SetSubscription(user_repo)

    updated = await use_case.execute(1, MediaSourceKind.EPIC, True)

    assert updated.apod_subscribed is True
