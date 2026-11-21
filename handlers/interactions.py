from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import (
    ContactStatus,
    InquiryStatus,
    ReportReason,
)
from database.repositories import interactions, listings as listing_repo, users as user_repo
from handlers.common import answer, require_user
from keyboards.inline import (
    ContactCB,
    FilterCB,
    InqCB,
    choices_kb,
    inquiry_actions_kb,
    yes_no_kb,
)
from keyboards.reply import main_menu_kb, skip_kb
from states.profile import CommonFlow
from utils.i18n import I18n, make_i18n
from utils.validators import clean_text

router = Router(name="interactions")

PURPOSES = ("buy", "rent", "view", "other")


def _user_i18n(user: object | None) -> I18n:
    language = getattr(user, "language", None) or "uz"
    return make_i18n(settings.locales_dir, language)


def _purpose_label(value: str, i18n: I18n) -> str:
    if value in PURPOSES:
        return i18n.t(f"inquiry.purpose_{value}")
    return value or i18n.t("inquiry.purpose_other")


async def _send_owner_inquiry(
    bot: Bot | None,
    session: AsyncSession,
    listing: object,
    requester: object,
    inquiry: object,
    message: str,
    consent: bool,
) -> None:
    owner = await user_repo.get_by_id(session, listing.user_id)
    owner_i18n = _user_i18n(owner)
    if owner is None or bot is None:
        return
    text = owner_i18n.t(
        "inquiry.new_inquiry",
        title=escape(listing.title or ""),
        name=escape(requester.display_name),
        username=escape(requester.username or "—"),
        purpose=_purpose_label(inquiry.purpose, owner_i18n),
        message=escape(message),
        phone=escape(requester.phone or "—") if consent else "—",
    )
    try:
        await bot.send_message(
            owner.telegram_id,
            text,
            parse_mode="HTML",
            reply_markup=inquiry_actions_kb(owner_i18n, inquiry.id),
        )
    except TelegramAPIError:
        pass
    await interactions.create_notification(
        session, owner.id, "new_inquiry", {"name": requester.display_name}
    )


# ---------------- Inquiry flow ----------------

@router.message(CommonFlow.inquiry_name)
async def collect_inquiry_name(message: Message, state, user: object | None, i18n: I18n) -> None:
    if not await require_user(message, user, i18n):
        return
    name = clean_text(message.text, 128)
    if name == i18n.t("common.skip") or len(name) < 2:
        name = message.from_user.full_name
    data = await state.get_data()
    data["inquiry_name"] = name
    await state.set_data(data)
    await state.set_state(CommonFlow.inquiry_purpose)
    await message.answer(
        i18n.t("inquiry.ask_purpose"),
        reply_markup=choices_kb(
            i18n,
            [(i18n.t(f"inquiry.purpose_{value}"), value) for value in PURPOSES],
            "inquiry_purpose",
            with_skip=False,
        ),
    )


@router.callback_query(CommonFlow.inquiry_purpose, FilterCB.filter(F.action == "inquiry_purpose"))
async def collect_inquiry_purpose(
    callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    data["inquiry_purpose"] = callback_data.value
    await state.set_data(data)
    await state.set_state(CommonFlow.inquiry_message)
    await answer(callback, i18n.t("inquiry.ask_message"), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.message(CommonFlow.inquiry_message)
async def collect_inquiry_message(message: Message, state, i18n: I18n) -> None:
    text = message.text or ""
    if text != i18n.t("common.skip"):
        text = clean_text(text, 1000)
    else:
        text = i18n.t("inquiry.default_message")
    data = await state.get_data()
    data["inquiry_message"] = text
    await state.set_data(data)
    await state.set_state(CommonFlow.inquiry_phone)
    await message.answer(i18n.t("inquiry.ask_phone_consent"), reply_markup=yes_no_kb(i18n))


@router.message(CommonFlow.inquiry_phone)
async def finish_inquiry(
    message: Message,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
) -> None:
    if not await require_user(message, user, i18n):
        return
    consent = (message.text or "").strip() == i18n.t("common.yes")
    data = await state.get_data()
    listing = await listing_repo.get(session, data.get("inquiry_listing_id", 0))
    if not listing:
        await state.clear()
        await message.answer(i18n.t("common.not_found"), reply_markup=main_menu_kb(i18n))
        return

    inquiry = await interactions.create_inquiry(
        session,
        listing.id,
        user.id,
        name=data.get("inquiry_name") or user.display_name,
        purpose=data.get("inquiry_purpose") or "other",
        message=data.get("inquiry_message") or "",
        phone_shared=consent,
    )
    await interactions.create_contact_request(
        session,
        listing_id=listing.id,
        inquiry_id=inquiry.id,
        owner_id=listing.user_id,
        requester_id=user.id,
        requester_consent=consent,
    )
    await _send_owner_inquiry(
        bot,
        session,
        listing,
        user,
        inquiry,
        data.get("inquiry_message") or "",
        consent,
    )
    await state.clear()
    await message.answer(i18n.t("inquiry.sent"), reply_markup=main_menu_kb(i18n))


# ---------------- Owner actions ----------------

async def _inquiry_context(
    session: AsyncSession, inquiry_id: int
) -> tuple[object | None, object | None]:
    inquiry = await interactions.get_inquiry(session, inquiry_id)
    listing = await listing_repo.get_simple(session, inquiry.listing_id) if inquiry else None
    return inquiry, listing


@router.callback_query(InqCB.filter())
async def inquiry_action(
    callback: CallbackQuery,
    callback_data: InqCB,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
    state,
    is_admin: bool,
) -> None:
    inquiry, listing = await _inquiry_context(session, callback_data.id)
    if not inquiry or not listing:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    if not is_admin and (user is None or listing.user_id != user.id):
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return

    if callback_data.action == "reply":
        data = await state.get_data()
        data["inquiry_reply_id"] = inquiry.id
        await state.set_data(data)
        await state.set_state(CommonFlow.inquiry_reply)
        await answer(callback, i18n.t("inquiry.ask_message"), reply_markup=skip_kb(i18n))
    elif callback_data.action == "contact":
        requester = await user_repo.get_by_id(session, inquiry.from_user_id)
        requester_i18n = _user_i18n(requester)
        owner = await user_repo.get_by_id(session, listing.user_id)
        phone = (listing.contact_phone or (owner.phone if owner else "") or "").strip()
        if requester and phone:
            try:
                await bot.send_message(
                    requester.telegram_id,
                    requester_i18n.t("inquiry.contact_shared_requester", phone=escape(phone)),
                    parse_mode="HTML",
                )
            except TelegramAPIError:
                pass
            await interactions.create_notification(
                session, requester.id, "contact_shared", {"phone": phone}
            )
        await answer(callback, i18n.t("contact.accepted"))
    else:
        inquiry.status = InquiryStatus.DECLINED
        requester = await user_repo.get_by_id(session, inquiry.from_user_id)
        requester_i18n = _user_i18n(requester)
        if requester:
            try:
                await bot.send_message(requester.telegram_id, requester_i18n.t("inquiry.declined"))
            except TelegramAPIError:
                pass
        await answer(callback, i18n.t("inquiry.declined"))
    await callback.answer()


@router.message(CommonFlow.inquiry_reply)
async def send_inquiry_reply(
    message: Message,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
    is_admin: bool,
) -> None:
    data = await state.get_data()
    inquiry, listing = await _inquiry_context(session, data.get("inquiry_reply_id", 0))
    if not inquiry or not listing:
        await state.clear()
        await message.answer(i18n.t("common.not_found"))
        return
    if not is_admin and (user is None or listing.user_id != user.id):
        await state.clear()
        await message.answer(i18n.t("common.access_denied"))
        return

    reply = clean_text(message.text, 1000)
    if not reply:
        await message.answer(i18n.t("inquiry.ask_message"))
        return
    inquiry.reply_message = reply
    inquiry.status = InquiryStatus.REPLIED
    requester = await user_repo.get_by_id(session, inquiry.from_user_id)
    requester_i18n = _user_i18n(requester)
    if requester:
        try:
            await bot.send_message(
                requester.telegram_id,
                requester_i18n.t("inquiry.owner_reply", message=escape(reply)),
                parse_mode="HTML",
            )
        except TelegramAPIError:
            pass
        await interactions.create_notification(
            session, requester.id, "inquiry_reply", {"message": reply}
        )
    await state.clear()
    await message.answer(i18n.t("inquiry.replied"), reply_markup=main_menu_kb(i18n))


@router.callback_query(ContactCB.filter())
async def contact_request_action(
    callback: CallbackQuery,
    callback_data: ContactCB,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    bot: Bot,
    is_admin: bool,
) -> None:
    request = await interactions.get_contact_request(session, callback_data.id)
    if not request:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    if not is_admin and (user is None or request.owner_id != user.id):
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return

    requester = await user_repo.get_by_id(session, request.requester_id)
    requester_i18n = _user_i18n(requester)
    if callback_data.action == "accept":
        owner = await user_repo.get_by_id(session, request.owner_id)
        phone = (owner.phone if owner else "").strip()
        request.owner_consent = True
        request.status = ContactStatus.ACCEPTED
        if requester and phone:
            try:
                await bot.send_message(
                    requester.telegram_id,
                    requester_i18n.t("inquiry.contact_shared_requester", phone=escape(phone)),
                    parse_mode="HTML",
                )
            except TelegramAPIError:
                pass
            await interactions.create_notification(
                session, requester.id, "contact_shared", {"phone": phone}
            )
        await answer(callback, i18n.t("contact.accepted"))
    else:
        request.status = ContactStatus.DECLINED
        if requester:
            try:
                await bot.send_message(requester.telegram_id, requester_i18n.t("contact.declined"))
            except TelegramAPIError:
                pass
        await answer(callback, i18n.t("contact.declined"))
    await callback.answer()


# ---------------- Reports ----------------

@router.message(CommonFlow.report_details)
async def finish_report(
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
    listing = await listing_repo.get_simple(session, data.get("report_listing_id", 0))
    raw_reason = str(data.get("report_reason") or "other").upper()
    try:
        reason = ReportReason(raw_reason)
    except ValueError:
        reason = ReportReason.OTHER
    details = message.text or ""
    if details == i18n.t("common.skip"):
        details = ""
    details = clean_text(details, 1000) or None

    await interactions.create_report(
        session,
        reporter_id=user.id,
        listing_id=listing.id if listing else None,
        reason=reason.value,
        details=details,
    )

    admin_i18n = make_i18n(settings.locales_dir, "uz")
    text = admin_i18n.t(
        "report.new_report",
        title=escape(listing.title if listing else "—"),
        reason=admin_i18n.t(f"report.{reason.value.lower()}"),
        details=escape(details or "—"),
        username=escape(user.username or "—"),
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="HTML")
        except TelegramAPIError:
            pass

    await state.clear()
    await message.answer(i18n.t("report.sent"), reply_markup=main_menu_kb(i18n))
