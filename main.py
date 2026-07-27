from __future__ import annotations

import asyncio
import logging
from datetime import date

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

import config
from application.epic.refresh_availability import RefreshEpicAvailability
from application.media.broadcast import BroadcastSubscribedUsers
from application.media.deliver_media import DeliverMediaForDate
from application.media.deliver_media_range import DeliverMediaForDateRange
from application.media.source_adapters import ApodSourceAdapter, EpicSourceAdapter
from application.subscriptions.manage_subscription import SetSubscription
from application.users.register_user import GetOrCreateUser
from domain.media.value_objects import MediaSourceKind
from infrastructure.db.models import Base
from infrastructure.db.repositories import SqlAlchemyApodRepository, SqlAlchemyEpicRepository, SqlAlchemyUserRepository
from infrastructure.db.session import build_engine, build_session_factory
from infrastructure.nasa.apod_client import ApodProvider
from infrastructure.nasa.epic_availability_client import EpicAvailabilityClient
from infrastructure.nasa.epic_client import EpicProvider
from infrastructure.telegram.admin_chat_gateway import TelegramAdminChatGateway
from infrastructure.translation.ru_translator import GoogleRuTranslator
from presentation.telegram.routers.apod_router import build_apod_router
from presentation.telegram.routers.epic_router import build_epic_router
from presentation.telegram.routers.start_router import build_start_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Раз в сутки: обновить список известных NASA дат EPIC + разослать подписчикам
# обоих источников. Один asyncio-цикл полностью закрывает эту потребность —
# AsyncIOScheduler ради одной периодической задачи не заводим (см.
# TZ-core-transfer.md, «Решения»).
PERIODIC_UPDATE_INTERVAL_SECONDS = 86400


async def periodic_broadcast(
    refresh_epic_availability: RefreshEpicAvailability,
    broadcast_epic: BroadcastSubscribedUsers,
    broadcast_apod: BroadcastSubscribedUsers,
) -> None:
    while True:
        today = date.today()
        logger.info("Запуск суточного обновления: доступность EPIC + рассылки")
        await refresh_epic_availability.execute()
        await broadcast_epic.execute(today)
        await broadcast_apod.execute(today)
        await asyncio.sleep(PERIODIC_UPDATE_INTERVAL_SECONDS)


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands([BotCommand(command="/start", description="Начать")], scope=BotCommandScopeDefault())


async def main() -> None:
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    engine = build_engine(config.DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = build_session_factory(engine)

    apod_repo = SqlAlchemyApodRepository(session_factory)
    epic_repo = SqlAlchemyEpicRepository(session_factory)
    user_repo = SqlAlchemyUserRepository(session_factory)

    async with aiohttp.ClientSession() as http_session:
        translator = GoogleRuTranslator()
        apod_provider = ApodProvider(http_session, config.NASA_API_KEY, config.NASA_APOD_URL, translator)
        epic_provider = EpicProvider(http_session, config.NASA_API_KEY, config.NASA_EPIC_URL)
        epic_availability = EpicAvailabilityClient(http_session, config.NASA_API_KEY, config.NASA_EPIC_URL)

        admin_chat_gateway = TelegramAdminChatGateway(http_session, bot, config.ADMIN_CHAT_ID)

        deliver_apod = DeliverMediaForDate(ApodSourceAdapter(apod_provider, apod_repo, admin_chat_gateway))
        deliver_epic = DeliverMediaForDate(EpicSourceAdapter(epic_provider, epic_repo, admin_chat_gateway))
        deliver_apod_range = DeliverMediaForDateRange(deliver_apod)

        get_or_create_user = GetOrCreateUser(user_repo)
        set_subscription = SetSubscription(user_repo, get_or_create_user)
        refresh_epic_availability = RefreshEpicAvailability(epic_availability, epic_repo)
        broadcast_apod = BroadcastSubscribedUsers(MediaSourceKind.APOD, deliver_apod, user_repo)
        broadcast_epic = BroadcastSubscribedUsers(MediaSourceKind.EPIC, deliver_epic, user_repo)

        dp.include_router(build_start_router(get_or_create_user))
        dp.include_router(
            build_apod_router(
                deliver_apod, deliver_apod_range, set_subscription, get_or_create_user, config.APOD_LOWER_BOUND
            )
        )
        dp.include_router(build_epic_router(deliver_epic, set_subscription, get_or_create_user))

        await bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(periodic_broadcast(refresh_epic_availability, broadcast_epic, broadcast_apod))

        await set_bot_commands(bot)
        logger.info("Бот запущен и ожидает обновлений.")
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
