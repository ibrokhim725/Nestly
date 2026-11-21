from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database.db import init_db
from handlers import setup_routers
from middlewares.database import DatabaseMiddleware
from middlewares.language import UserContextMiddleware
from middlewares.throttling import ThrottlingMiddleware
from services.scheduler import setup_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("nestly")


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.outer_middleware(ThrottlingMiddleware())
    dispatcher.update.outer_middleware(DatabaseMiddleware())
    dispatcher.update.outer_middleware(UserContextMiddleware())
    setup_routers(dispatcher)
    return dispatcher


async def run_webhook(bot: Bot, dispatcher: Dispatcher) -> None:
    from aiohttp import web

    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    await bot.set_webhook(
        settings.webhook_url + settings.webhook_path,
        secret_token=settings.webhook_secret,
        drop_pending_updates=True,
    )
    app = web.Application()
    SimpleRequestHandler(
        dispatcher=dispatcher, bot=bot, secret_token=settings.webhook_secret
    ).register(app, path=settings.webhook_path)
    setup_application(app, dispatcher, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.webhook_host, settings.webhook_port)
    await site.start()
    logger.info("webhook started on %s:%s", settings.webhook_host, settings.webhook_port)
    await asyncio.Event().wait()


async def main() -> None:
    await init_db()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dispatcher = build_dispatcher()
    scheduler = setup_scheduler(bot)
    try:
        if settings.mode == "webhook":
            await run_webhook(bot, dispatcher)
        else:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("polling started")
            await dispatcher.start_polling(bot)
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
