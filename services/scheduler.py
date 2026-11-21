from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import Bot

from config import settings
from database.db import AsyncSessionLocal
from database.models import ListingStatus
from database.repositories import listings as listing_repo
from database.repositories import users as user_repo
from services.notification_service import notify
from utils.i18n import make_i18n

logger = logging.getLogger(__name__)


async def remind_expiring(bot: Bot) -> None:
    async with AsyncSessionLocal() as session:
        items = await listing_repo.get_expiring(session, settings.expiry_reminder_days)
        for listing in items:
            owner = await user_repo.get_by_id(session, listing.user_id)
            i18n = make_i18n(settings.locales_dir, owner.language if owner else "uz")
            await notify(
                bot,
                session,
                listing.user_id,
                i18n,
                "listing_expiring",
                {"title": listing.title},
            )
            listing.expiry_notified_at = datetime.now(timezone.utc)
        await session.commit()
        if items:
            logger.info("expiry reminders sent: %s", len(items))


async def expire_listings(bot: Bot) -> None:
    async with AsyncSessionLocal() as session:
        items = await listing_repo.expire_old(session)
        for listing in items:
            listing.status = ListingStatus.EXPIRED
            owner = await user_repo.get_by_id(session, listing.user_id)
            i18n = make_i18n(settings.locales_dir, owner.language if owner else "uz")
            await notify(
                bot,
                session,
                listing.user_id,
                i18n,
                "listing_expired",
                {"title": listing.title},
            )
        await session.commit()
        if items:
            logger.info("listings expired: %s", len(items))


def setup_scheduler(bot: Bot):
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
    except ImportError:
        logger.warning("APScheduler is not installed; scheduler disabled")
        return None

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        remind_expiring,
        trigger="interval",
        hours=6,
        args=[bot],
        id="remind_expiring",
        replace_existing=True,
    )
    scheduler.add_job(
        expire_listings,
        trigger="interval",
        hours=1,
        args=[bot],
        id="expire_listings",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started")
    return scheduler
