from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from handlers.common import MenuTextFilter, answer, require_user
from keyboards.inline import NavCB
from keyboards.reply import main_menu_kb
from utils.i18n import I18n

router = Router(name="menu")


@router.message(F.text == "/menu")
@router.message(MenuTextFilter("common.main_menu"))
async def show_main(message: Message, user: object | None, i18n: I18n, is_admin: bool) -> None:
    if not await require_user(message, user, i18n):
        return
    await message.answer(i18n.t("menu.main"), reply_markup=main_menu_kb(i18n, is_admin))


@router.callback_query(NavCB.filter(F.action == "main"))
async def nav_main(callback: CallbackQuery, user: object | None, i18n: I18n, is_admin: bool) -> None:
    if not await require_user(callback, user, i18n):
        await callback.answer()
        return
    await answer(callback, i18n.t("menu.main"), reply_markup=main_menu_kb(i18n, is_admin))
    await callback.answer()


@router.callback_query(NavCB.filter(F.action == "cancel"))
async def nav_cancel(callback: CallbackQuery, state, i18n: I18n, is_admin: bool) -> None:
    await state.clear()
    await answer(callback, i18n.t("listing.cancelled"), reply_markup=main_menu_kb(i18n, is_admin))
    await callback.answer()
