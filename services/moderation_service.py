from __future__ import annotations

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Listing, ListingStatus, ModerationAction
from database.repositories import interactions, listings as listing_repo
from services.notification_service import notify
from utils.i18n import I18n


async def _log(session, admin_id: int, action: ModerationAction, listing: Listing, reason: str | None):
    await interactions.add_moderation_log(
        session,
        admin_id=admin_id,
        action=action.value,
        listing_id=listing.id,
        reason=reason,
    )


async def approve(
    session: AsyncSession, bot: Bot | None, admin_id: int, listing: Listing, i18n: I18n
) -> None:
    listing.status = ListingStatus.ACTIVE
    listing.rejection_reason = None
    listing.is_suspicious = False
    await _log(session, admin_id, ModerationAction.APPROVE, listing, None)
    await notify(
        bot, session, listing.user_id, i18n, "listing_approved", {"title": listing.title}
    )
    await session.flush()


async def reject(
    session: AsyncSession,
    bot: Bot | None,
    admin_id: int,
    listing: Listing,
    reason: str,
    i18n: I18n,
) -> None:
    listing.status = ListingStatus.REJECTED
    listing.rejection_reason = reason
    await _log(session, admin_id, ModerationAction.REJECT, listing, reason)
    await notify(
        bot,
        session,
        listing.user_id,
        i18n,
        "listing_rejected",
        {"title": listing.title, "reason": reason},
    )
    await session.flush()


async def request_fix(
    session: AsyncSession,
    bot: Bot | None,
    admin_id: int,
    listing: Listing,
    reason: str,
    i18n: I18n,
) -> None:
    listing.status = ListingStatus.REJECTED
    listing.rejection_reason = reason
    await _log(session, admin_id, ModerationAction.REQUEST_FIX, listing, reason)
    await notify(
        bot,
        session,
        listing.user_id,
        i18n,
        "listing_rejected",
        {"title": listing.title, "reason": reason},
    )
    await session.flush()


async def mark_suspicious(
    session: AsyncSession, bot: Bot | None, admin_id: int, listing: Listing
) -> None:
    listing.is_suspicious = True
    await _log(session, admin_id, ModerationAction.MARK_SUSPICIOUS, listing, None)
    await session.flush()


async def change_status(
    session: AsyncSession,
    bot: Bot | None,
    listing: Listing,
    status: ListingStatus,
    i18n: I18n,
) -> None:
    listing.status = status
    if status in {ListingStatus.SOLD, ListingStatus.RENTED, ListingStatus.ARCHIVED}:
        user_ids = await interactions.favorite_user_ids(session, listing.id)
        await notify_many_favorites(bot, session, user_ids, listing, i18n)
    await session.flush()


async def notify_many_favorites(
    bot: Bot | None, session: AsyncSession, user_ids: list[int], listing: Listing, i18n: I18n
) -> None:
    from services.notification_service import notify_many

    await notify_many(
        bot, session, user_ids, i18n, "favorite_sold", {"title": listing.title}
    )
