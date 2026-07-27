from datetime import date

from application.media.broadcast import BroadcastSubscribedUsers
from domain.media.exceptions import MediaNotAvailable
from domain.media.value_objects import MediaSourceKind
from domain.users.entities import User
from tests.application.fakes import FakeUserRepository


class DeliverStub:
    def __init__(self, fail_for: set[int] | None = None) -> None:
        self.fail_for = fail_for or set()
        self.calls: list[tuple[date, int]] = []

    async def execute(self, day: date, chat_id: int) -> None:
        self.calls.append((day, chat_id))
        if chat_id in self.fail_for:
            raise MediaNotAvailable("no data yet")


async def test_broadcast_continues_past_users_with_no_media_available():
    users = [User(chat_id=1, apod_subscribed=True), User(chat_id=2, apod_subscribed=True)]
    user_repo = FakeUserRepository(users)
    deliver = DeliverStub(fail_for={1})
    broadcast = BroadcastSubscribedUsers(MediaSourceKind.APOD, deliver, user_repo)

    await broadcast.execute(date(2024, 1, 1))

    assert deliver.calls == [(date(2024, 1, 1), 1), (date(2024, 1, 1), 2)]


async def test_broadcast_only_targets_subscribed_users():
    users = [User(chat_id=1, apod_subscribed=True), User(chat_id=2, apod_subscribed=False)]
    user_repo = FakeUserRepository(users)
    deliver = DeliverStub()
    broadcast = BroadcastSubscribedUsers(MediaSourceKind.APOD, deliver, user_repo)

    await broadcast.execute(date(2024, 1, 1))

    assert deliver.calls == [(date(2024, 1, 1), 1)]
