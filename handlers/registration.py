from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import ProfileType, UserStatus
from database.repositories import users as user_repo
from handlers.common import answer
from keyboards.inline import ConfirmCB, FilterCB, profile_type_kb, terms_kb
from keyboards.reply import contact_kb, main_menu_kb
from states.registration import Registration
from utils.i18n import I18n, make_i18n
from utils.validators import clean_text, is_valid_phone, normalize_phone

router = Router(name="registration")

LANGUAGE_MAP = {
    "🇺🇿 O‘zbek tili": "uz",
    "🇷🇺 Русский язык": "ru",
}


@router.message(Registration.language, F.text.in_(LANGUAGE_MAP.keys()))
async def choose_language(
    message: Message,
    state,
    user: object | None,
    session: AsyncSession,
    i18n: I18n,
) -> None:
    lang = LANGUAGE_MAP[message.text]
    if user is None:
        user = await user_repo.create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            language=lang,
        )
    else:
        await user_repo.set_language(session, user, lang)
    new_i18n = make_i18n(settings.locales_dir, lang)
    await state.set_data({"language": lang})
    await state.set_state(Registration.terms)
    await message.answer(new_i18n.t("language.saved"))
    await message.answer(
        new_i18n.t("legal.terms"),
        parse_mode="HTML",
        reply_markup=terms_kb(new_i18n),
    )


@router.callback_query(Registration.terms, ConfirmCB.filter(F.action == "terms_yes"))
async def accept_terms(callback: CallbackQuery, state, i18n: I18n) -> None:
    data = await state.get_data()
    data["terms"] = True
    await state.set_data(data)
    await state.set_state(Registration.first_name)
    await answer(callback, i18n.t("registration.first_name"))
    await callback.answer()


@router.callback_query(Registration.terms, ConfirmCB.filter(F.action == "terms_no"))
async def decline_terms(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("registration.terms_required"), reply_markup=terms_kb(i18n))
    await callback.answer()


@router.message(Registration.first_name)
async def ask_last_name(message: Message, state, i18n: I18n) -> None:
    value = clean_text(message.text, 128)
    if len(value) < 2:
        await message.answer(i18n.t("registration.first_name"))
        return
    data = await state.get_data()
    data["first_name"] = value
    await state.set_data(data)
    await state.set_state(Registration.last_name)
    await message.answer(i18n.t("registration.last_name"))


@router.message(Registration.last_name)
async def ask_phone(message: Message, state, i18n: I18n) -> None:
    value = clean_text(message.text, 128)
    if len(value) < 2:
        await message.answer(i18n.t("registration.last_name"))
        return
    data = await state.get_data()
    data["last_name"] = value
    await state.set_data(data)
    await state.set_state(Registration.phone)
    await message.answer(i18n.t("registration.phone"), reply_markup=contact_kb(i18n))


@router.message(Registration.phone, F.contact)
async def get_phone(
    message: Message,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
) -> None:
    contact: Contact | None = message.contact
    if contact is None or contact.user_id != message.from_user.id:
        await message.answer(i18n.t("registration.phone_invalid"), reply_markup=contact_kb(i18n))
        return
    if not is_valid_phone(contact.phone_number):
        await message.answer(i18n.t("registration.phone_invalid"), reply_markup=contact_kb(i18n))
        return
    phone = normalize_phone(contact.phone_number)
    existing = await user_repo.find_by_phone(session, phone, exclude_user_id=user.id if user else 0)
    if existing:
        await message.answer(i18n.t("registration.phone_mismatch"), reply_markup=contact_kb(i18n))
        return
    data = await state.get_data()
    data["phone"] = phone
    await state.set_data(data)
    await state.set_state(Registration.profile_type)
    await message.answer(i18n.t("registration.profile_type"), reply_markup=profile_type_kb(i18n))


@router.message(Registration.phone)
async def phone_not_shared(message: Message, i18n: I18n) -> None:
    await message.answer(i18n.t("registration.phone_invalid"), reply_markup=contact_kb(i18n))


@router.callback_query(Registration.profile_type, FilterCB.filter(F.action == "profile_type"))
async def finish_registration(
    callback: CallbackQuery,
    callback_data: FilterCB,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
) -> None:
    if user is None:
        await callback.answer(i18n.t("common.error"), show_alert=True)
        return
    data = await state.get_data()
    if not data.get("terms") or not data.get("first_name") or not data.get("last_name") or not data.get("phone"):
        await callback.answer(i18n.t("common.error"), show_alert=True)
        return
    profile_type = ProfileType(callback_data.value)
    await user_repo.complete_registration(
        session,
        user,
        first_name=data["first_name"],
        last_name=data["last_name"],
        phone=data["phone"],
        profile_type=profile_type,
    )
    await state.clear()
    await answer(
        callback,
        i18n.t("registration.success"),
        reply_markup=main_menu_kb(i18n, False),
    )
    await callback.answer()
