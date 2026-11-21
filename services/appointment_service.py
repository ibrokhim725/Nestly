from __future__ import annotations

from typing import Any

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ViewingRequest, ViewingStatus
from database.repositories import interactions
from services.notification_service import notify
from utils.i18n import I18n


async def create_viewing(
    session: AsyncSession,
    bot: Bot | None,
    listing: Any,
    requester: Any,
    visit_date: str,
    visit_time: str,
    note: str | None,
    owner_i18n: I18n,
) -> ViewingRequest:
    viewing = await interactions.create_viewing(
        session,
        listing_id=listing.id,
        owner_id=listing.user_id,
        requester_id=requester.id,
        visit_date=visit_date,
        visit_time=visit_time,
        note=note,
    )
    await notify(
        bot,
        session,
        listing.user_id,
        owner_i18n,
        "viewing_new",
        {
            "title": listing.title,
            "name": requester.display_name,
            "date": visit_date,
            "time": visit_time,
            "note": note or "—",
        },
    )
    await session.flush()
    return viewing


async def respond(
    session: AsyncSession,
    bot: Bot | None,
    viewing: ViewingRequest,
    action: str,
    recipient_i18n: I18n,
    proposed_date: str | None = None,
    proposed_time: str | None = None,
) -> None:
    if action == "confirm":
        viewing.status = ViewingStatus.CONFIRMED
        code = "viewing_confirmed"
        payload = {"date": viewing.visit_date, "time": viewing.visit_time}
    elif action == "reschedule":
        viewing.status = ViewingStatus.RESCHEDULED
        viewing.proposed_date = proposed_date
        viewing.proposed_time = proposed_time
        code = "viewing_reschedule"
        payload = {
            "date": proposed_date or viewing.visit_date,
            "time": proposed_time or viewing.visit_time,
        }
    elif action == "cancel":
        viewing.status = ViewingStatus.CANCELLED
        code = "viewing_cancelled"
        payload = {}
    else:
        viewing.status = ViewingStatus.DECLINED
        code = "viewing_declined"
        payload = {}
    await notify(bot, session, viewing.requester_id, recipient_i18n, code, payload)
    await session.flush()
