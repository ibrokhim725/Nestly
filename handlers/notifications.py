from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import interactions, listings as listing_repo, users as user_repo
from handlers.common import MenuTextFilter, require_user
from keyboards.inline import (
    contact_actions_kb,
    inquiry_actions_kb,
    notifications_kb,
)
from services.notification_service import format_notification
from utils.i18n import I18n

router = Router(name="notifications")


@router.message(MenuTextFilter("menu.notifications"))
async def show_notifications(
    message: Message,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
) -> None:
    if not await require_user(message, user, i18n):
        return

    items = await interactions.list_notifications(session, user.id, limit=10)
    unread = await interactions.unread_count(session, user.id)

    lines = [i18n.t("notifications.title")]
    if unread:
        lines.append(i18n.t("notifications.unread", count=unread))
    if items:
        lines.extend(format_notification(item, i18n) for item in items)
    else:
        lines.append(i18n.t("notifications.empty"))

    await message.answer(
        "\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=notifications_kb(i18n, unread),
    )

    inquiries = await interactions.list_inquiries_for_owner(session, user.id)
    pending = [
        item
        for item in inquiries
        if str(getattr(item.status, "value", item.status)) == "PENDING"
    ][:10]
    for inquiry in pending:
        listing = await listing_repo.get_simple(session, inquiry.listing_id)
        requester = await user_repo.get_by_id(session, inquiry.from_user_id)
        if not listing or not requester:
            continue
        text = i18n.t(
            "inquiry.new_inquiry",
            title=escape(listing.title or ""),
            name=escape(requester.display_name),
            username=escape(requester.username or "—"),
            purpose=i18n.t(f"inquiry.purpose_{inquiry.purpose}")
            if inquiry.purpose in {"buy", "rent", "view", "other"}
            else escape(inquiry.purpose or "—"),
            message=escape(inquiry.message or ""),
            phone=escape(requester.phone or "—"),
        )
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=inquiry_actions_kb(i18n, inquiry.id),
        )

    contacts = await interactions.list_pending_contacts(session, user.id)
    for request in contacts[:10]:
        requester = await user_repo.get_by_id(session, request.requester_id)
        if not requester:
            continue
        await message.answer(
            f"{i18n.t('contact.request')}\n👤 {escape(requester.display_name)}",
            reply_markup=contact_actions_kb(i18n, request.id),
        )
