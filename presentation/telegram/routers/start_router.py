from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from application.users.register_user import GetOrCreateUser
from presentation.telegram.keyboards.start_kb import get_start_kb

WELCOME_TEXT = "Добро пожаловать! Выберите интересующий раздел, чтобы начать"


def build_start_router(get_or_create_user: GetOrCreateUser) -> Router:
    router = Router()

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext) -> None:
        await state.clear()
        await get_or_create_user.execute(message.chat.id)
        await message.answer(WELCOME_TEXT, reply_markup=get_start_kb())

    @router.callback_query(F.data == "back_to_start")
    async def cmd_start_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
        await callback_query.message.delete()
        await state.clear()
        await callback_query.message.answer(WELCOME_TEXT, reply_markup=get_start_kb())

    return router
