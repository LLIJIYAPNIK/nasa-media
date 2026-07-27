from datetime import date

from application.users.send_birthday_greetings import SendBirthdayGreetings
from domain.media.exceptions import MediaNotAvailable
from domain.users.entities import User
from tests.application.fakes import FakeGreetingSender, FakeUserRepository

TODAY = date(2026, 3, 15)


class DeliverStub:
    def __init__(self, fail_for: set[int] | None = None) -> None:
        self.fail_for = fail_for or set()
        self.calls: list[tuple[date, int]] = []

    async def execute(self, day: date, chat_id: int) -> None:
        self.calls.append((day, chat_id))
        if chat_id in self.fail_for:
            raise MediaNotAvailable("no data yet")


async def test_greets_only_users_whose_birthday_is_today():
    users = [
        User(chat_id=1, birthday=date(1990, 3, 15)),
        User(chat_id=2, birthday=date(1990, 3, 16)),
        User(chat_id=3, birthday=None),
    ]
    user_repo = FakeUserRepository(users)
    deliver = DeliverStub()
    greeting_sender = FakeGreetingSender()
    use_case = SendBirthdayGreetings(deliver, user_repo, greeting_sender)

    await use_case.execute(TODAY)

    assert deliver.calls == [(TODAY, 1)]
    assert [chat_id for chat_id, _ in greeting_sender.sent] == [1]


async def test_skips_greeting_when_media_not_available_but_does_not_crash():
    users = [User(chat_id=1, birthday=date(1990, 3, 15))]
    user_repo = FakeUserRepository(users)
    deliver = DeliverStub(fail_for={1})
    greeting_sender = FakeGreetingSender()
    use_case = SendBirthdayGreetings(deliver, user_repo, greeting_sender)

    await use_case.execute(TODAY)

    assert deliver.calls == [(TODAY, 1)]
    assert greeting_sender.sent == []


async def test_birthday_greeting_does_not_require_apod_subscription():
    users = [User(chat_id=1, apod_subscribed=False, birthday=date(1990, 3, 15))]
    user_repo = FakeUserRepository(users)
    deliver = DeliverStub()
    greeting_sender = FakeGreetingSender()
    use_case = SendBirthdayGreetings(deliver, user_repo, greeting_sender)

    await use_case.execute(TODAY)

    assert deliver.calls == [(TODAY, 1)]
