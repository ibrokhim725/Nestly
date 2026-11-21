from __future__ import annotations

from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserStatus
from database.repositories import interactions, users
from utils.i18n import I18n

CODE_TO_KEY = {
    "listing_approved": "notifications.listing_approved",
    "listing_rejected": "notifications.listing_rejected",
    "listing_expiring": "notifications.listing_expiring",
    "listing_expired": "notifications.listing_expired",
    "saved_search_match": "notifications.saved_search_match",
    "admin_message": "notifications.admin_message",
    "new_inquiry": "notifications.new_inquiry",
    "contact_request": "notifications.contact_request",
    "viewing_new": "viewing.new_request",
    "viewing_confirmed": "viewing.owner_confirmed",
    "viewing_declined": "viewing.owner_declined",
    "viewing_cancelled": "viewing.owner_cancelled",
    "viewing_reschedule": "viewing.propose_new",
    "viewing_requester_cancelled": "viewing.requester_cancelled",
    "favorite_sold": "favorites.notify_sold",
    "profile_warning": "notifications.admin_message",
    "inquiry_reply": "inquiry.owner_reply",
    "contact_shared": "inquiry.contact_shared_requester",
}


def render(i18n: I18n, code: str, payload: dict[str, Any]) -> str:
    key = CODE_TO_KEY.get(code, "notifications.admin_message")
    try:
        return i18n.t(key, **payload)
    except Exception:
        return i18n.t(key)


async def notify(
    bot: Bot | None,
    session: AsyncSession,
    user_id: int,
    i18n: I18n,
    code: str,
    payload: dict[str, Any] | None = None,
) -> bool:
    payload = payload or {}
    user = await users.get_by_id(session, user_id)
    if not user or user.status in {UserStatus.BLOCKED, UserStatus.DELETED}:
        return False
    await interactions.create_notification(session, user_id, code, payload)
    if not user.notifications_enabled or bot is None:
        return False
    text = render(i18n, code, payload)
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            parse_mode="HTML",
        )
        return True
    except TelegramAPIError:
        return False


async def notify_many(
    bot: Bot | None,
    session: AsyncSession,
    user_ids: list[int],
    i18n: I18n,
    code: str,
    payload: dict[str, Any] | None = None,
) -> int:
    sent = 0
    for user_id in set(user_ids):
        if await notify(bot, session, user_id, i18n, code, payload):
            sent += 1
    return sent


def format_notification(item: Any, i18n: I18n) -> str:
    return render(i18n, item.code, item.payload or {})
