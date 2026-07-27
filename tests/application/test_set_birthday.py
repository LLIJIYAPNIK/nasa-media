from datetime import date

from application.users.register_user import GetOrCreateUser
from application.users.set_birthday import SetBirthday
from tests.application.fakes import FakeUserRepository


def _use_case(user_repo: FakeUserRepository) -> SetBirthday:
    return SetBirthday(user_repo, GetOrCreateUser(user_repo))


async def test_set_birthday_saves_date_for_existing_user():
    user_repo = FakeUserRepository()
    await user_repo.add(chat_id=1)
    use_case = _use_case(user_repo)

    updated = await use_case.execute(1, date(1990, 5, 20))

    assert updated.birthday == date(1990, 5, 20)
    persisted = await user_repo.get_by_chat_id(1)
    assert persisted is not None
    assert persisted.birthday == date(1990, 5, 20)


async def test_set_birthday_registers_user_when_missing():
    user_repo = FakeUserRepository()
    use_case = _use_case(user_repo)

    updated = await use_case.execute(42, date(1990, 5, 20))

    assert updated.chat_id == 42
    assert updated.birthday == date(1990, 5, 20)
