from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import (
    District,
    Listing,
    ListingStatus,
    ModerationAction,
    Region,
    ReportStatus,
    SearchLog,
    User,
    UserStatus,
)
from database.repositories import interactions, listings as listing_repo, users as user_repo
from handlers.common import MenuTextFilter, answer, require_admin
from keyboards.inline import (
    AdminCB,
    PageCB,
    PubCB,
    ReportCB,
    admin_menu_kb,
    broadcast_kb,
    button,
    inquiry_actions_kb,
    moderation_kb,
    regions_admin_kb,
    report_actions_kb,
    stats_period_kb,
    user_manage_kb,
    viewing_actions_kb,
)
from keyboards.reply import main_menu_kb, skip_kb
from services import moderation_service
from states.profile import CommonFlow
from utils.formatters import format_full_listing, format_listing_card
from utils.i18n import I18n, make_i18n
from utils.pagination import total_pages
from utils.validators import clean_text, parse_int

router = Router(name="admin")

TEXT_PAGE_SIZE = 5
ONE_PAGE_SIZE = 1


def _paged_nav(i18n: I18n, scope: str, page: int, total: int, per_page: int):
    pages = total_pages(total, per_page)
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(
            text=i18n.t("common.prev"),
            callback_data=PageCB(scope=scope, page=page - 1).pack(),
        )
    builder.button(text=f"{page}/{pages}", callback_data="noop")
    if page < pages:
        builder.button(
            text=i18n.t("common.next"),
            callback_data=PageCB(scope=scope, page=page + 1).pack(),
        )
    builder.adjust(3)
    builder.row(button(i18n.t("admin.back"), AdminCB(action="menu")))
    return builder.as_markup()


def _format_stats(rows: list[tuple[str, int]], i18n: I18n) -> str:
    if not rows:
        return i18n.t("common.none")
    return ", ".join(f"{escape(str(name))} ({count})" for name, count in rows)


async def _count(session: AsyncSession, model: object) -> int:
    return int(await session.scalar(select(func.count(model.id))) or 0)


# ---------------- Menu ----------------

@router.message(MenuTextFilter("menu.admin"))
async def admin_menu_message(message: Message, i18n: I18n, is_admin: bool) -> None:
    if not await require_admin(message, {"is_admin": is_admin}, i18n):
        return
    await message.answer(
        i18n.t("admin.title"), parse_mode="HTML", reply_markup=admin_menu_kb(i18n)
    )


@router.callback_query(AdminCB.filter())
async def admin_callback(
    callback: CallbackQuery,
    callback_data: AdminCB,
    session: AsyncSession,
    i18n: I18n,
    is_admin: bool,
    bot: Bot,
    state,
) -> None:
    if not is_admin:
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return

    action = callback_data.action
    value = callback_data.value

    if action == "menu":
        await answer(callback, i18n.t("admin.title"), parse_mode="HTML", reply_markup=admin_menu_kb(i18n))
    elif action == "stats":
        await answer(callback, i18n.t("admin.stats"), reply_markup=stats_period_kb(i18n))
    elif action in {"stats_day", "stats_week", "stats_month"}:
        await show_stats(callback, session, i18n, action.split("_", 1)[1])
    elif action == "pending":
        await show_pending(callback, session, i18n, 1)
    elif action == "all_listings":
        await show_all_listings(callback, session, i18n, 1)
    elif action == "users":
        await show_users(callback, session, i18n, 1)
    elif action == "inquiries":
        await show_inquiries(callback, session, i18n)
    elif action == "viewings":
        await show_viewings(callback, session, i18n)
    elif action == "reports":
        await show_reports(callback, session, i18n)
    elif action == "regions":
        await answer(callback, i18n.t("admin.regions_title"), reply_markup=regions_admin_kb(i18n))
    elif action == "settings":
        await show_settings(callback, i18n)
    elif action == "activity":
        await show_activity(callback, session, i18n)
    elif action == "broadcast":
        await answer(callback, i18n.t("admin.broadcast_title"), reply_markup=broadcast_kb(i18n))
    elif action == "add_region":
        await state.set_state(CommonFlow.region_name_uz)
        await answer(callback, i18n.t("admin.ask_region_name_uz"), reply_markup=main_menu_kb(i18n, True))
    elif action == "add_district":
        await state.set_state(CommonFlow.district_region_id)
        await answer(callback, i18n.t("admin.ask_district_region"), reply_markup=main_menu_kb(i18n, True))
    elif action == "seg":
        await choose_broadcast_segment(callback, session, i18n, state, value)
    elif action == "seg_region":
        await set_broadcast_region(callback, i18n, state, value)
    elif action == "warn":
        await state.set_state(CommonFlow.warning_message)
        await state.update_data(target_user_id=int(value) if value.isdigit() else 0)
        await answer(callback, i18n.t("admin.ask_warning"), reply_markup=skip_kb(i18n))
    elif action in {"block_temp", "block_perm", "unblock"}:
        await manage_user_block(callback, session, i18n, bot, action, value)
    await callback.answer()


# ---------------- Stats ----------------

async def show_stats(event, session: AsyncSession, i18n: I18n, period: str) -> None:
    days = {"day": 1, "week": 7, "month": 30}.get(period, 1)
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    counts = await listing_repo.count_by_status(session)
    top_regions = await listing_repo.top_regions(session, 5)
    top_types = await interactions.top_search_types(session, since, 5)

    text = i18n.t(
        "admin.stats_body",
        period=i18n.t(f"admin.{period}"),
        total_users=await user_repo.count_users(session),
        new_today=await user_repo.count_new_since(session, now - timedelta(days=1)),
        active_users=await user_repo.count_active_users(session, since),
        total_listings=sum(counts.values()),
        active_listings=counts.get("ACTIVE", 0),
        pending_listings=counts.get("PENDING", 0),
        rejected_listings=counts.get("REJECTED", 0),
        sold=counts.get("SOLD", 0),
        rented=counts.get("RENTED", 0),
        top_regions=_format_stats(top_regions, i18n),
        top_types=_format_stats(top_types, i18n),
    )
    await answer(event, text, parse_mode="HTML", reply_markup=stats_period_kb(i18n))


# ---------------- Listings ----------------

async def show_pending(event, session: AsyncSession, i18n: I18n, page: int) -> None:
    items = await listing_repo.list_by_status(session, [ListingStatus.PENDING])
    if not items:
        await answer(event, i18n.t("admin.no_pending"), reply_markup=admin_menu_kb(i18n))
        return
    page = max(1, min(page, len(items)))
    listing = items[page - 1]
    full = await listing_repo.get(session, listing.id)
    await answer(
        event,
        format_full_listing(full or listing, i18n),
        parse_mode="HTML",
        reply_markup=moderation_kb(i18n, listing.id),
    )
    await answer(
        event,
        i18n.t("admin.pending"),
        reply_markup=_paged_nav(i18n, "admin_pending", page, len(items), ONE_PAGE_SIZE),
    )


async def show_all_listings(event, session: AsyncSession, i18n: I18n, page: int) -> None:
    total = await _count(session, Listing)
    if total == 0:
        await answer(event, i18n.t("admin.no_items"), reply_markup=admin_menu_kb(i18n))
        return
    page = max(1, min(page, total_pages(total, TEXT_PAGE_SIZE)))
    items = await listing_repo.list_all(
        session, limit=TEXT_PAGE_SIZE, offset=(page - 1) * TEXT_PAGE_SIZE
    )
    text = "\n\n➖➖➖\n\n".join(format_listing_card(item, i18n) for item in items)
    await answer(
        event,
        f"{i18n.t('admin.all_listings')}\n\n{text}",
        parse_mode="HTML",
        reply_markup=_paged_nav(i18n, "admin_all", page, total, TEXT_PAGE_SIZE),
    )


# ---------------- Users ----------------

async def show_users(event, session: AsyncSession, i18n: I18n, page: int) -> None:
    total = await _count(session, User)
    if total == 0:
        await answer(event, i18n.t("admin.no_items"), reply_markup=admin_menu_kb(i18n))
        return
    page = max(1, min(page, total_pages(total, ONE_PAGE_SIZE)))
    items = await user_repo.list_users(
        session, limit=ONE_PAGE_SIZE, offset=(page - 1) * ONE_PAGE_SIZE
    )
    for item in items:
        text = i18n.t(
            "admin.user_card",
            id=item.id,
            tg=item.telegram_id,
            name=escape(item.display_name),
            phone=escape(item.phone or "—"),
            lang=item.language.upper(),
            status=str(getattr(item.status, "value", item.status)),
            listings=await listing_repo.count_by_user(session, item.id),
        )
        await answer(event, text, parse_mode="HTML", reply_markup=user_manage_kb(i18n, item.id))
    await answer(
        event,
        i18n.t("admin.users"),
        reply_markup=_paged_nav(i18n, "admin_users", page, total, ONE_PAGE_SIZE),
    )


# ---------------- Inquiries / viewings / reports ----------------

async def show_inquiries(event, session: AsyncSession, i18n: I18n) -> None:
    items = await interactions.list_all_inquiries(session, limit=20)
    if not items:
        await answer(event, i18n.t("admin.no_items"), reply_markup=admin_menu_kb(i18n))
        return
    for inquiry in items:
        listing = await listing_repo.get_simple(session, inquiry.listing_id)
        requester = await user_repo.get_by_id(session, inquiry.from_user_id)
        purpose = (
            i18n.t(f"inquiry.purpose_{inquiry.purpose}")
            if inquiry.purpose in {"buy", "rent", "view", "other"}
            else escape(inquiry.purpose or "—")
        )
        text = "\n".join(
            [
                f"<b>{i18n.t('inquiry.title')}</b>",
                f"🏠 {escape(listing.title) if listing else '—'}",
                f"👤 {escape(requester.display_name) if requester else '—'}",
                f"🎯 {purpose}",
                f"💬 {escape(inquiry.message or '—')}",
                f"📞 {escape(requester.phone if requester and requester.phone else '—')}",
                f"📌 {str(getattr(inquiry.status, 'value', inquiry.status))}",
            ]
        )
        await answer(
            event,
            text,
            parse_mode="HTML",
            reply_markup=inquiry_actions_kb(i18n, inquiry.id),
        )


async def show_viewings(event, session: AsyncSession, i18n: I18n) -> None:
    items = await interactions.list_all_viewings(session, limit=20)
    if not items:
        await answer(event, i18n.t("admin.no_items"), reply_markup=admin_menu_kb(i18n))
        return
    for viewing in items:
        listing = await listing_repo.get_simple(session, viewing.listing_id)
        status = str(getattr(viewing.status, "value", viewing.status))
        text = i18n.t(
            "viewing.item",
            title=escape(listing.title) if listing else "—",
            date=viewing.visit_date,
            time=viewing.visit_time,
            status=i18n.t(f"viewing_status.{status.lower()}"),
        )
        await answer(event, text, reply_markup=viewing_actions_kb(i18n, viewing.id))


async def show_reports(event, session: AsyncSession, i18n: I18n) -> None:
    items = await interactions.list_reports(session, open_only=True)
    if not items:
        await answer(event, i18n.t("admin.no_reports"), reply_markup=admin_menu_kb(i18n))
        return
    for report in items:
        reporter = await user_repo.get_by_id(session, report.reporter_id)
        listing = (
            await listing_repo.get_simple(session, report.listing_id)
            if report.listing_id
            else None
        )
        text = i18n.t(
            "admin.report_item",
            reason=i18n.t(f"report.{str(getattr(report.reason, 'value', report.reason)).lower()}"),
            username=escape(reporter.username or "—") if reporter else "—",
            title=escape(listing.title) if listing else "—",
            details=escape(report.details or "—"),
        )
        await answer(event, text, reply_markup=report_actions_kb(i18n, report.id))


# ---------------- Settings / activity ----------------

async def show_settings(event, i18n: I18n) -> None:
    text = i18n.t(
        "admin.settings_body",
        mode=settings.mode,
        ttl=settings.listing_ttl_days,
        reminder=settings.expiry_reminder_days,
        min_images=settings.min_listing_images,
        max_images=settings.max_listing_images,
        limit=settings.max_active_listings_per_user,
        rate=settings.rate_limit_seconds,
    )
    await answer(event, text, parse_mode="HTML", reply_markup=admin_menu_kb(i18n))


async def show_activity(event, session: AsyncSession, i18n: I18n) -> None:
    logs = await interactions.list_moderation_logs(session, limit=30)
    if not logs:
        await answer(event, i18n.t("admin.activity_empty"), reply_markup=admin_menu_kb(i18n))
        return
    lines = [i18n.t("admin.activity_title")]
    for log in logs:
        lines.append(
            i18n.t(
                "admin.activity_item",
                id=log.id,
                action=str(getattr(log.action, "value", log.action)),
                admin_id=log.admin_id,
                target=log.target_user_id or log.listing_id or "—",
                date=log.created_at.strftime("%d.%m.%Y %H:%M"),
            )
        )
    await answer(
        event,
        "\n".join(lines),
        reply_markup=admin_menu_kb(i18n),
    )


# ---------------- Moderation ----------------

@router.callback_query(PubCB.filter())
async def moderate_listing(
    callback: CallbackQuery,
    callback_data: PubCB,
    session: AsyncSession,
    i18n: I18n,
    is_admin: bool,
    bot: Bot,
    state,
) -> None:
    if not is_admin:
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return
    listing = await listing_repo.get(session, callback_data.id)
    if not listing:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return

    action = callback_data.action
    if action == "approve":
        await moderation_service.approve(session, bot, callback.from_user.id, listing, i18n)
        await answer(callback, i18n.t("admin.approved"), reply_markup=moderation_kb(i18n, listing.id))
    elif action in {"reject", "fix"}:
        await state.set_state(
            CommonFlow.reject_reason if action == "reject" else CommonFlow.fix_reason
        )
        await state.update_data(moderation_listing_id=listing.id)
        await answer(callback, i18n.t("admin.ask_reject_reason"), reply_markup=skip_kb(i18n))
    elif action == "suspicious":
        await moderation_service.mark_suspicious(session, bot, callback.from_user.id, listing)
        await answer(callback, i18n.t("admin.marked_suspicious"), reply_markup=moderation_kb(i18n, listing.id))
    await callback.answer()


@router.message(CommonFlow.reject_reason)
@router.message(CommonFlow.fix_reason)
async def apply_moderation_reason(
    message: Message,
    state,
    session: AsyncSession,
    i18n: I18n,
    is_admin: bool,
    bot: Bot,
) -> None:
    if not is_admin:
        await state.clear()
        return
    reason = clean_text(message.text, 500)
    if not reason:
        await message.answer(i18n.t("admin.reason_required"), reply_markup=skip_kb(i18n))
        return
    data = await state.get_data()
    listing = await listing_repo.get(session, data.get("moderation_listing_id", 0))
    current = await state.get_state()
    if not listing:
        await state.clear()
        await message.answer(i18n.t("common.not_found"))
        return
    if current == CommonFlow.fix_reason.state:
        await moderation_service.request_fix(
            session, bot, message.from_user.id, listing, reason, i18n
        )
        await message.answer(i18n.t("admin.fix_requested"), reply_markup=main_menu_kb(i18n, True))
    else:
        await moderation_service.reject(
            session, bot, message.from_user.id, listing, reason, i18n
        )
        await message.answer(i18n.t("admin.rejected"), reply_markup=main_menu_kb(i18n, True))
    await state.clear()


@router.callback_query(ReportCB.filter())
async def report_action(
    callback: CallbackQuery,
    callback_data: ReportCB,
    session: AsyncSession,
    i18n: I18n,
    is_admin: bool,
) -> None:
    if not is_admin:
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return
    report = await interactions.get_report(session, callback_data.id)
    if not report:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    if callback_data.action == "resolve":
        report.status = ReportStatus.RESOLVED
        log_action = ModerationAction.REPORT_RESOLVED
        text = i18n.t("admin.resolved")
    else:
        report.status = ReportStatus.DISMISSED
        log_action = ModerationAction.REPORT_DISMISSED
        text = i18n.t("admin.dismissed")
    await interactions.add_moderation_log(
        session,
        admin_id=callback.from_user.id,
        action=log_action.value,
        listing_id=report.listing_id,
    )
    await answer(callback, text, reply_markup=admin_menu_kb(i18n))
    await callback.answer()


# ---------------- Users management ----------------

async def manage_user_block(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    bot: Bot,
    action: str,
    value: str,
) -> None:
    if not value.isdigit():
        return
    user_id = int(value)
    target = await user_repo.get_by_id(session, user_id)
    if not target:
        await answer(callback, i18n.t("common.not_found"))
        return

    if action == "unblock":
        await user_repo.unblock_user(session, user_id)
        await interactions.add_moderation_log(
            session,
            admin_id=callback.from_user.id,
            action=ModerationAction.UNBLOCK.value,
            target_user_id=user_id,
        )
        await answer(callback, i18n.t("admin.unblocked"))
        return

    target_i18n = make_i18n(settings.locales_dir, target.language)
    try:
        await bot.send_message(
            target.telegram_id,
            target_i18n.t("notifications.admin_message", message=i18n.t("admin.blocked")),
            parse_mode="HTML",
        )
    except TelegramAPIError:
        pass

    permanent = action == "block_perm"
    await user_repo.create_block(
        session,
        user_id=user_id,
        admin_id=callback.from_user.id,
        reason="admin",
        permanent=permanent,
        days=None if permanent else 7,
    )
    await interactions.add_moderation_log(
        session,
        admin_id=callback.from_user.id,
        action=ModerationAction.BLOCK.value,
        target_user_id=user_id,
    )
    await answer(callback, i18n.t("admin.blocked"))


@router.message(CommonFlow.warning_message)
async def send_warning(
    message: Message,
    state,
    session: AsyncSession,
    i18n: I18n,
    bot: Bot,
    is_admin: bool,
) -> None:
    if not is_admin:
        await state.clear()
        return
    data = await state.get_data()
    target = await user_repo.get_by_id(session, data.get("target_user_id", 0))
    text = clean_text(message.text, 1000)
    if not target or not text:
        await state.clear()
        await message.answer(i18n.t("common.not_found"))
        return
    target_i18n = make_i18n(settings.locales_dir, target.language)
    try:
        await bot.send_message(
            target.telegram_id,
            target_i18n.t("notifications.admin_message", message=escape(text)),
            parse_mode="HTML",
        )
    except TelegramAPIError:
        pass
    await interactions.create_notification(session, target.id, "admin_message", {"message": text})
    await interactions.add_moderation_log(
        session,
        admin_id=message.from_user.id,
        action=ModerationAction.WARN.value,
        target_user_id=target.id,
        reason=text,
    )
    await state.clear()
    await message.answer(i18n.t("admin.warn_sent"), reply_markup=main_menu_kb(i18n, True))


# ---------------- Regions ----------------

@router.message(CommonFlow.region_name_uz)
async def region_name_uz(message: Message, state, i18n: I18n) -> None:
    value = clean_text(message.text, 128)
    if len(value) < 2:
        await message.answer(i18n.t("admin.ask_region_name_uz"))
        return
    await state.update_data(region_name_uz=value)
    await state.set_state(CommonFlow.region_name_ru)
    await message.answer(i18n.t("admin.ask_region_name_ru"))


@router.message(CommonFlow.region_name_ru)
async def region_name_ru(message: Message, state, i18n: I18n) -> None:
    value = clean_text(message.text, 128)
    if len(value) < 2:
        await message.answer(i18n.t("admin.ask_region_name_ru"))
        return
    await state.update_data(region_name_ru=value)
    await state.set_state(CommonFlow.region_code)
    await message.answer(i18n.t("admin.ask_region_code"))


@router.message(CommonFlow.region_code)
async def region_code(message: Message, state, session: AsyncSession, i18n: I18n, is_admin: bool) -> None:
    if not is_admin:
        await state.clear()
        return
    code = clean_text(message.text, 64).lower().replace(" ", "_")
    if len(code) < 2:
        await message.answer(i18n.t("admin.ask_region_code"))
        return
    exists = await session.scalar(select(Region.id).where(Region.code == code))
    if exists:
        await message.answer(i18n.t("common.error"), reply_markup=main_menu_kb(i18n, True))
        await state.clear()
        return
    data = await state.get_data()
    session.add(
        Region(
            code=code,
            name_uz=data.get("region_name_uz", code),
            name_ru=data.get("region_name_ru", code),
        )
    )
    await interactions.add_moderation_log(
        session,
        admin_id=message.from_user.id,
        action=ModerationAction.REGION_ADD.value,
        reason=code,
    )
    await state.clear()
    await message.answer(i18n.t("admin.region_added"), reply_markup=main_menu_kb(i18n, True))


@router.message(CommonFlow.district_region_id)
async def district_region_id(message: Message, state, session: AsyncSession, i18n: I18n) -> None:
    region_id = parse_int(message.text)
    region = await session.get(Region, region_id) if region_id else None
    if not region:
        await message.answer(i18n.t("admin.ask_district_region"))
        return
    await state.update_data(district_region_id=region.id)
    await state.set_state(CommonFlow.district_name_uz)
    await message.answer(i18n.t("admin.ask_district_name_uz"))


@router.message(CommonFlow.district_name_uz)
async def district_name_uz(message: Message, state, i18n: I18n) -> None:
    value = clean_text(message.text, 128)
    if len(value) < 2:
        await message.answer(i18n.t("admin.ask_district_name_uz"))
        return
    await state.update_data(district_name_uz=value)
    await state.set_state(CommonFlow.district_name_ru)
    await message.answer(i18n.t("admin.ask_district_name_ru"))


@router.message(CommonFlow.district_name_ru)
async def district_name_ru(
    message: Message, state, session: AsyncSession, i18n: I18n, is_admin: bool
) -> None:
    if not is_admin:
        await state.clear()
        return
    value = clean_text(message.text, 128)
    if len(value) < 2:
        await message.answer(i18n.t("admin.ask_district_name_ru"))
        return
    data = await state.get_data()
    session.add(
        District(
            region_id=data.get("district_region_id", 0),
            name_uz=data.get("district_name_uz", value),
            name_ru=value,
        )
    )
    await interactions.add_moderation_log(
        session,
        admin_id=message.from_user.id,
        action=ModerationAction.DISTRICT_ADD.value,
        reason=value,
    )
    await state.clear()
    await message.answer(i18n.t("admin.district_added"), reply_markup=main_menu_kb(i18n, True))


# ---------------- Broadcast ----------------

async def choose_broadcast_segment(
    callback: CallbackQuery,
    session: AsyncSession,
    i18n: I18n,
    state,
    segment: str,
) -> None:
    if segment == "region":
        regions = list(
            (
                await session.execute(
                    select(Region).where(Region.is_active.is_(True)).order_by(Region.id)
                )
            )
            .scalars()
            .all()
        )
        builder = InlineKeyboardBuilder()
        for region in regions:
            name = getattr(region, f"name_{i18n.lang}", None) or region.name_uz
            builder.button(text=name, callback_data=AdminCB(action="seg_region", value=str(region.id)))
        builder.adjust(2)
        builder.row(button(i18n.t("admin.back"), AdminCB(action="broadcast")))
        await answer(callback, i18n.t("admin.select_region_segment"), reply_markup=builder.as_markup())
        return
    await state.set_state(CommonFlow.broadcast_message)
    await state.update_data(broadcast_segment=segment)
    await answer(callback, i18n.t("admin.ask_message"), reply_markup=skip_kb(i18n))


async def set_broadcast_region(
    callback: CallbackQuery, i18n: I18n, state, value: str
) -> None:
    if not value.isdigit():
        return
    await state.set_state(CommonFlow.broadcast_message)
    await state.update_data(broadcast_segment=f"region:{value}")
    await answer(callback, i18n.t("admin.ask_message"), reply_markup=skip_kb(i18n))


async def _segment_users(session: AsyncSession, segment: str) -> list[User]:
    query = select(User).where(
        User.status == UserStatus.ACTIVE,
        User.notifications_enabled.is_(True),
    )
    if segment == "searchers":
        query = query.where(
            User.id.in_(select(SearchLog.user_id).where(SearchLog.user_id.is_not(None)))
        )
    elif segment == "posters":
        query = query.where(User.id.in_(select(Listing.user_id)))
    elif segment.startswith("region:"):
        region_id = parse_int(segment.split(":", 1)[1])
        if region_id:
            search_users = select(SearchLog.user_id).where(
                SearchLog.user_id.is_not(None), SearchLog.region_id == region_id
            )
            listing_users = select(Listing.user_id).where(Listing.region_id == region_id)
            query = query.where(User.id.in_(search_users.union(listing_users)))
    result = await session.execute(query)
    return list(result.scalars().all())


@router.message(CommonFlow.broadcast_message)
async def run_broadcast(
    message: Message,
    state,
    session: AsyncSession,
    i18n: I18n,
    bot: Bot,
    is_admin: bool,
) -> None:
    if not is_admin:
        await state.clear()
        return
    text = clean_text(message.text, 3000)
    if not text:
        await message.answer(i18n.t("admin.ask_message"))
        return
    data = await state.get_data()
    segment = data.get("broadcast_segment") or "all"
    targets = await _segment_users(session, segment)
    sent = 0
    for target in targets:
        target_i18n = make_i18n(settings.locales_dir, target.language)
        try:
            await bot.send_message(
                target.telegram_id,
                target_i18n.t("notifications.admin_message", message=escape(text)),
                parse_mode="HTML",
            )
            sent += 1
        except TelegramAPIError:
            continue
        await interactions.create_notification(
            session, target.id, "admin_message", {"message": text}
        )
    await interactions.create_broadcast(
        session,
        admin_id=message.from_user.id,
        segment=segment,
        message=text,
        recipients=sent,
    )
    await interactions.add_moderation_log(
        session,
        admin_id=message.from_user.id,
        action=ModerationAction.BROADCAST.value,
        reason=segment,
    )
    await state.clear()
    await message.answer(
        i18n.t("admin.broadcast_done", count=sent), reply_markup=main_menu_kb(i18n, True)
    )


# ---------------- Pagination ----------------

@router.callback_query(PageCB.filter(F.scope.startswith("admin_")))
async def admin_page(
    callback: CallbackQuery,
    callback_data: PageCB,
    session: AsyncSession,
    i18n: I18n,
    is_admin: bool,
) -> None:
    if not is_admin:
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return
    if callback_data.scope == "admin_pending":
        await show_pending(callback, session, i18n, callback_data.page)
    elif callback_data.scope == "admin_all":
        await show_all_listings(callback, session, i18n, callback_data.page)
    elif callback_data.scope == "admin_users":
        await show_users(callback, session, i18n, callback_data.page)
    await callback.answer()
