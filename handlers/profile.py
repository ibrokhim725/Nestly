from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Contact, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import ProfileType, UserStatus
from database.repositories import interactions, listings as listing_repo, users as user_repo
from handlers.common import MenuTextFilter, answer, require_user
from keyboards.inline import (
    ProfileCB,
    SavedCB,
    edit_profile_kb,
    language_kb,
    legal_kb,
    profile_kb,
    profile_type_kb,
    saved_search_kb,
)
from keyboards.reply import main_menu_kb
from states.profile import EditProfile
from utils.formatters import summarize_filters
from utils.i18n import I18n

router = Router(name="profile")

LANGUAGE_MAP = {
    "🇺🇿 O‘zbek tili": "uz",
    "🇷🇺 Русский язык": "ru",
}


def verified_text(i18n: I18n, value: bool) -> str:
    return i18n.t("profile.verified" if value else "profile.not_verified")


@router.message(MenuTextFilter("menu.my_profile"))
async def show_profile(message: Message, session, user, i18n: I18n) -> None:
    if not await require_user(message, user, i18n):
        return
    total = await listing_repo.count_by_user(session, user.id)
    from database.models import ListingStatus

    active = await listing_repo.count_by_user_and_status(session, user.id, ListingStatus.ACTIVE)
    text = i18n.t(
        "profile.body",
        name=user.display_name,
        phone=user.phone or "—",
        username=user.username or "—",
        ptype=i18n.t(f"profile_type.{user.profile_type.value.lower()}") if user.profile_type else "—",
        lang=user.language.upper(),
        registered=user.created_at.strftime("%d.%m.%Y") if user.created_at else "—",
        total=total,
        active=active,
        phone_v=verified_text(i18n, user.is_phone_verified),
        profile_v=verified_text(i18n, user.is_profile_verified),
        docs_v=verified_text(i18n, user.is_documents_verified),
        notice=i18n.t("profile.safety_notice"),
    )
    await message.answer(text, parse_mode="HTML", reply_markup=profile_kb(i18n))


@router.callback_query(ProfileCB.filter(F.action == "edit"))
async def edit_profile(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("profile.edit"), reply_markup=edit_profile_kb(i18n))
    await callback.answer()


@router.callback_query(ProfileCB.filter(F.action.in_(["edit_first_name", "edit_last_name", "edit_phone", "edit_profile_type", "edit_language"])))
async def choose_profile_edit(
    callback: CallbackQuery, callback_data: ProfileCB, i18n: I18n, state
) -> None:
    mapping = {
        "edit_first_name": (EditProfile.first_name, "profile.edit_name"),
        "edit_last_name": (EditProfile.last_name, "profile.edit_last_name"),
        "edit_phone": (EditProfile.phone, "profile.edit_phone"),
        "edit_profile_type": (EditProfile.profile_type, "registration.profile_type"),
        "edit_language": (EditProfile.language, "profile.edit_language"),
    }
    fsm_state, prompt = mapping[callback_data.action]
    await state.set_state(fsm_state)
    markup = None
    if callback_data.action == "edit_profile_type":
        markup = profile_type_kb(i18n)
    elif callback_data.action == "edit_language":
        markup = language_kb()
    elif callback_data.action == "edit_phone":
        from keyboards.reply import contact_kb

        markup = contact_kb(i18n)
    await answer(callback, i18n.t(prompt), reply_markup=markup)
    await callback.answer()


@router.message(EditProfile.first_name)
@router.message(EditProfile.last_name)
async def update_name(message: Message, state, session, user, i18n: I18n) -> None:
    current = await state.get_state()
    value = (message.text or "").strip()[:128]
    if len(value) < 2:
        await message.answer(i18n.t("profile.updated"))
        return
    if current == EditProfile.first_name.state:
        user.profile.first_name = value
    else:
        user.profile.last_name = value
    await state.clear()
    await message.answer(i18n.t("profile.updated"), reply_markup=main_menu_kb(i18n))


@router.message(EditProfile.phone, F.contact)
async def update_phone(message: Message, state, session, user, i18n: I18n) -> None:
    contact: Contact | None = message.contact
    if not contact or contact.user_id != message.from_user.id:
        await message.answer(i18n.t("registration.phone_mismatch"))
        return
    from utils.validators import is_valid_phone, normalize_phone

    if not is_valid_phone(contact.phone_number):
        await message.answer(i18n.t("registration.phone_invalid"))
        return
    phone = normalize_phone(contact.phone_number)
    existing = await user_repo.find_by_phone(session, phone, exclude_user_id=user.id)
    if existing:
        await message.answer(i18n.t("registration.phone_mismatch"))
        return
    user.profile.phone = phone
    await state.clear()
    await message.answer(i18n.t("profile.updated"), reply_markup=main_menu_kb(i18n))


@router.callback_query(EditProfile.profile_type, F.data.startswith("fl:profile_type:"))
async def update_profile_type(
    callback: CallbackQuery, session, user, i18n: I18n, state
) -> None:
    value = callback.data.rsplit(":", 1)[1]
    user.profile.profile_type = ProfileType(value)
    await state.clear()
    await answer(callback, i18n.t("profile.updated"), reply_markup=main_menu_kb(i18n))
    await callback.answer()


@router.message(EditProfile.language)
async def update_language(message: Message, state, session, user, i18n: I18n) -> None:
    lang = LANGUAGE_MAP.get(message.text or "")
    if not lang:
        await message.answer(i18n.t("language.invalid"), reply_markup=language_kb())
        return
    from utils.i18n import make_i18n

    await user_repo.set_language(session, user, lang)
    await state.clear()
    new_i18n = make_i18n(settings.locales_dir, lang)
    await message.answer(new_i18n.t("language.changed"), reply_markup=main_menu_kb(new_i18n))


@router.callback_query(ProfileCB.filter(F.action == "notifications"))
async def notification_settings(callback: CallbackQuery, session, user, i18n: I18n) -> None:
    text = i18n.t(
        "profile.notif_enabled" if user.notifications_enabled else "profile.notif_disabled"
    )
    builder = InlineKeyboardBuilder()
    from keyboards.inline import button, ProfileCB as PCB

    builder.button(text=i18n.t("profile.toggle_notif"), callback_data=PCB(action="toggle_notif").pack())
    builder.button(text=i18n.t("common.back"), callback_data=PCB(action="back").pack())
    builder.adjust(1)
    await answer(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(ProfileCB.filter(F.action == "toggle_notif"))
async def toggle_notifications(callback: CallbackQuery, session, user, i18n: I18n) -> None:
    await user_repo.set_notifications(session, user, not user.notifications_enabled)
    text = i18n.t("profile.notif_enabled" if user.notifications_enabled else "profile.notif_disabled")
    await notification_settings(callback, session, user, i18n)
    await callback.answer(text)


@router.callback_query(ProfileCB.filter(F.action == "back"))
async def profile_back(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("profile.title"), reply_markup=profile_kb(i18n))
    await callback.answer()


@router.callback_query(ProfileCB.filter(F.action == "legal"))
async def profile_legal(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("legal.title"), reply_markup=legal_kb(i18n))
    await callback.answer()


@router.callback_query(ProfileCB.filter(F.action == "delete_request"))
async def delete_profile_request(callback: CallbackQuery, bot: Bot, user, i18n: I18n) -> None:
    text = i18n.t(
        "admin.delete_profile_request", name=user.display_name, username=user.username or "—"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass
    await answer(callback, i18n.t("profile.delete_sent"), reply_markup=main_menu_kb(i18n))
    await callback.answer()


@router.callback_query(ProfileCB.filter(F.action == "read_notifications"))
async def read_notifications(callback: CallbackQuery, session, user, i18n: I18n) -> None:
    await interactions.mark_all_read(session, user.id)
    await callback.answer(i18n.t("notifications.marked"))


@router.message(MenuTextFilter("menu.saved_searches"))
@router.callback_query(ProfileCB.filter(F.action == "saved_searches"))
async def show_saved_searches(event, session, user, i18n: I18n) -> None:
    items = await interactions.list_saved_searches(session, user.id)
    if not items:
        await answer(event, i18n.t("saved_search.empty"))
        return
    builder = InlineKeyboardBuilder()
    for item in items:
        label = f"{'🔔' if item.notify else '🔕'} {item.name}"
        builder.button(text=label[:60], callback_data=SavedCB(action="toggle", id=item.id).pack())
    builder.adjust(1)
    await answer(event, i18n.t("saved_search.title"), reply_markup=builder.as_markup())
