from application.users.register_user import GetOrCreateUser
from domain.users.entities import User
from tests.application.fakes import FakeUserRepository


async def test_returns_existing_user_without_creating_new_one():
    user_repo = FakeUserRepository([User(chat_id=1)])
    use_case = GetOrCreateUser(user_repo)

    user = await use_case.execute(1)

    assert user.chat_id == 1


async def test_creates_user_when_missing():
    user_repo = FakeUserRepository()
    use_case = GetOrCreateUser(user_repo)

    user = await use_case.execute(42)

    assert user.chat_id == 42
    assert await user_repo.get_by_chat_id(42) is not None
