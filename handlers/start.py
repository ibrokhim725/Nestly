from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import UserStatus
from database.repositories import users as user_repo
from handlers.common import MenuTextFilter, answer, require_admin
from keyboards.inline import (
    AdminCB,
    LegalCB,
    NavCB,
    admin_menu_kb,
    help_kb,
    language_kb,
    legal_kb,
    main_menu_kb,
)
from states.registration import Registration
from utils.i18n import I18n, make_i18n

router = Router(name="start")


@router.message(F.text == "/start")
async def cmd_start(
    message: Message,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
    state,
    is_admin: bool = False,
) -> None:
    if user and getattr(user.status, "value", user.status) == UserStatus.ACTIVE.value:
        await message.answer(i18n.t("menu.main"), reply_markup=main_menu_kb(i18n, is_admin))
        return
    await state.set_state(Registration.language)
    await message.answer(i18n.t("welcome"), reply_markup=language_kb())


@router.message(F.text == "/help")
@router.message(MenuTextFilter("menu.help"))
async def cmd_help(message: Message, i18n: I18n) -> None:
    await message.answer(i18n.t("help.title") + "\n\n" + i18n.t("help.body"), reply_markup=help_kb(i18n))


@router.message(F.text == "/id")
async def cmd_id(message: Message) -> None:
    await message.answer(f"🆔 Sizning Telegram ID: <code>{message.from_user.id}</code>")


@router.message(F.text == "/admin")
async def cmd_admin(
    message: Message, i18n: I18n, data: dict, is_admin: bool
) -> None:
    if not await require_admin(message, {"is_admin": is_admin}, i18n):
        return
    await message.answer(i18n.t("admin.title"), parse_mode="HTML", reply_markup=admin_menu_kb(i18n))


@router.callback_query(NavCB.filter(F.action == "legal"))
async def open_legal(callback: CallbackQuery, i18n: I18n) -> None:
    await callback.message.edit_text(i18n.t("legal.title"), reply_markup=legal_kb(i18n))
    await callback.answer()


@router.callback_query(LegalCB.filter())
async def show_legal(callback: CallbackQuery, callback_data: LegalCB, i18n: I18n) -> None:
    text = i18n.t(f"legal.{callback_data.doc}")
    from keyboards.inline import back_button

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=inline_back(i18n)
    )
    await callback.answer()


def inline_back(i18n: I18n):
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.t("common.back"), callback_data=NavCB(action="legal").pack())
    return builder.as_markup()


@router.callback_query(AdminCB.filter(F.action == "contact_admin"))
async def contact_admin(callback: CallbackQuery, i18n: I18n, bot: Bot, session: AsyncSession) -> None:
    await callback.answer(i18n.t("help.contact_admin"))
    await callback.message.answer(i18n.t("help.contact_info"), parse_mode="HTML")
