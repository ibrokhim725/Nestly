from __future__ import annotations

from datetime import date
from html import escape

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import ViewingStatus
from database.repositories import interactions, listings as listing_repo, users as user_repo
from handlers.common import MenuTextFilter, answer, require_user
from keyboards.inline import ViewCB, viewing_actions_kb
from keyboards.reply import main_menu_kb, skip_kb
from services import appointment_service
from services.notification_service import notify
from states.profile import CommonFlow
from utils.i18n import I18n, make_i18n
from utils.validators import clean_text, parse_date, parse_time

router = Router(name="appointments")


def _user_i18n(user: object | None) -> I18n:
    return make_i18n(settings.locales_dir, getattr(user, "language", None) or "uz")


@router.message(MenuTextFilter("menu.appointments"))
async def show_appointments(
    message: Message,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    is_admin: bool,
) -> None:
    if not await require_user(message, user, i18n):
        return
    items = await interactions.list_viewings(session, user.id)
    if not items:
        await message.answer(i18n.t("viewing.empty"), reply_markup=main_menu_kb(i18n, is_admin))
        return

    for viewing in items[:10]:
        listing = await listing_repo.get_simple(session, viewing.listing_id)
        title = escape(listing.title) if listing else "—"
        status = str(getattr(viewing.status, "value", viewing.status))
        text = i18n.t(
            "viewing.item",
            title=title,
            date=viewing.visit_date,
            time=viewing.visit_time,
            status=i18n.t(f"viewing_status.{status.lower()}"),
        )
        if viewing.proposed_date:
            text += "\n" + i18n.t(
                "viewing.propose_new",
                date=viewing.proposed_date,
                time=viewing.proposed_time or "",
            )
        text += "\n\n" + i18n.t("viewing.safety")
        markup = None
        if is_admin or viewing.owner_id == user.id:
            markup = viewing_actions_kb(i18n, viewing.id)
        elif viewing.requester_id == user.id and status not in {
            ViewingStatus.CANCELLED.value,
            ViewingStatus.DECLINED.value,
        }:
            builder = InlineKeyboardBuilder()
            builder.button(
                text=i18n.t("viewing.cancel"),
                callback_data=ViewCB(action="cancel", id=viewing.id).pack(),
            )
            markup = builder.as_markup()
        await message.answer(text, reply_markup=markup)


@router.message(CommonFlow.viewing_date)
async def collect_viewing_date(message: Message, state, i18n: I18n) -> None:
    value = parse_date(message.text)
    if not value or value < date.today():
        await message.answer(i18n.t("viewing.ask_date"), reply_markup=skip_kb(i18n))
        return
    data = await state.get_data()
    data["viewing_date"] = value.isoformat()
    await state.set_data(data)
    await state.set_state(CommonFlow.viewing_time)
    await message.answer(i18n.t("viewing.ask_time"))


@router.message(CommonFlow.viewing_time)
async def collect_viewing_time(message: Message, state, i18n: I18n) -> None:
    value = parse_time(message.text)
    if not value:
        await message.answer(i18n.t("viewing.ask_time"))
        return
    data = await state.get_data()
    data["viewing_time"] = value
    await state.set_data(data)
    await state.set_state(CommonFlow.viewing_note)
    await message.answer(i18n.t("viewing.ask_note"), reply_markup=skip_kb(i18n))


@router.message(CommonFlow.viewing_note)
async def finish_viewing(
    message: Message,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
) -> None:
    if not await require_user(message, user, i18n):
        return
    data = await state.get_data()
    listing = await listing_repo.get(session, data.get("viewing_listing_id", 0))
    if not listing:
        await state.clear()
        await message.answer(i18n.t("common.not_found"), reply_markup=main_menu_kb(i18n))
        return
    note = message.text or ""
    if note == i18n.t("common.skip"):
        note = ""
    owner = await user_repo.get_by_id(session, listing.user_id)
    await appointment_service.create_viewing(
        session,
        bot,
        listing,
        user,
        data.get("viewing_date"),
        data.get("viewing_time"),
        clean_text(note, 500) or None,
        _user_i18n(owner),
    )
    await state.clear()
    await message.answer(i18n.t("viewing.sent"), reply_markup=main_menu_kb(i18n))


@router.callback_query(ViewCB.filter())
async def viewing_action(
    callback: CallbackQuery,
    callback_data: ViewCB,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
    state,
    is_admin: bool,
) -> None:
    viewing = await interactions.get_viewing(session, callback_data.id)
    if not viewing:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return

    is_owner = bool(user and viewing.owner_id == user.id)
    is_requester = bool(user and viewing.requester_id == user.id)
    if not (is_admin or is_owner or is_requester):
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return

    action = callback_data.action
    if action == "reschedule":
        if not (is_admin or is_owner):
            await callback.answer(i18n.t("common.access_denied"), show_alert=True)
            return
        await state.set_state(CommonFlow.viewing_propose_date)
        await state.update_data(propose_viewing_id=viewing.id)
        await answer(callback, i18n.t("viewing.ask_date"), reply_markup=skip_kb(i18n))
        await callback.answer()
        return

    if action in {"confirm", "decline"} and not (is_admin or is_owner):
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return

    if action == "cancel" and is_requester and not (is_admin or is_owner):
        viewing.status = ViewingStatus.CANCELLED
        owner = await user_repo.get_by_id(session, viewing.owner_id)
        await notify(
            bot,
            session,
            viewing.owner_id,
            _user_i18n(owner),
            "viewing_requester_cancelled",
            {"date": viewing.visit_date, "time": viewing.visit_time},
        )
    else:
        requester = await user_repo.get_by_id(session, viewing.requester_id)
        await appointment_service.respond(
            session,
            bot,
            viewing,
            action,
            _user_i18n(requester),
        )

    key = {
        "confirm": "viewing.confirmed",
        "decline": "viewing.declined",
        "cancel": "viewing.cancelled",
    }.get(action, "common.error")
    await answer(callback, i18n.t(key))
    await callback.answer()


@router.message(CommonFlow.viewing_propose_date)
async def collect_proposed_date(message: Message, state, i18n: I18n) -> None:
    value = parse_date(message.text)
    if not value or value < date.today():
        await message.answer(i18n.t("viewing.ask_date"), reply_markup=skip_kb(i18n))
        return
    await state.update_data(proposed_date=value.isoformat())
    await state.set_state(CommonFlow.viewing_propose_time)
    await message.answer(i18n.t("viewing.ask_time"))


@router.message(CommonFlow.viewing_propose_time)
async def finish_proposal(
    message: Message,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
    is_admin: bool,
) -> None:
    value = parse_time(message.text)
    if not value:
        await message.answer(i18n.t("viewing.ask_time"))
        return
    data = await state.get_data()
    viewing = await interactions.get_viewing(session, data.get("propose_viewing_id", 0))
    if not viewing:
        await state.clear()
        await message.answer(i18n.t("common.not_found"))
        return
    if not is_admin and (user is None or viewing.owner_id != user.id):
        await state.clear()
        await message.answer(i18n.t("common.access_denied"))
        return

    requester = await user_repo.get_by_id(session, viewing.requester_id)
    await appointment_service.respond(
        session,
        bot,
        viewing,
        "reschedule",
        _user_i18n(requester),
        proposed_date=data.get("proposed_date"),
        proposed_time=value,
    )
    await state.clear()
    await message.answer(i18n.t("viewing.sent"), reply_markup=main_menu_kb(i18n, is_admin))
