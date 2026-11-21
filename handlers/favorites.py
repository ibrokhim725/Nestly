from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.repositories import interactions
from handlers.common import MenuTextFilter, answer, require_user
from keyboards.inline import CardCB, FavCB, NavCB, PageCB
from utils.formatters import format_listing_card
from utils.i18n import I18n
from utils.pagination import normalize_page, paginate

router = Router(name="favorites")


@router.message(MenuTextFilter("menu.favorites"))
async def show_favorites(message: Message, session, user, i18n: I18n, state) -> None:
    if not await require_user(message, user, i18n):
        return
    await state.clear()
    await render_favorites(message, session, user.id, i18n, 1, 0)


async def render_favorites(event, session, user_id: int, i18n: I18n, page: int, _unused: int = 0) -> None:
    items = await interactions.list_favorites(session, user_id)
    if not items:
        await answer(event, i18n.t("favorites.empty"))
        return
    page = normalize_page(page, len(items))
    listing = paginate(items, page, 1)[0]
    builder = InlineKeyboardBuilder()
    builder.button(
        text=i18n.t("listing_card.remove_favorite"),
        callback_data=FavCB(action="unfav", id=listing.id, page=page).pack(),
    )
    builder.button(
        text=i18n.t("listing_card.contact_owner"),
        callback_data=CardCB(action="contact", id=listing.id, page=page).pack(),
    )
    builder.adjust(1)
    nav = []
    if page > 1:
        nav.append(PageCB(scope="favorites", page=page - 1))
    nav.append(None)
    if page < len(items):
        nav.append(PageCB(scope="favorites", page=page + 1))
    row = []
    for item in nav:
        if item is None:
            row.append(InlineKeyboardButton(text=f"{page}/{len(items)}", callback_data="noop"))
        else:
            row.append(InlineKeyboardButton(text="⬅️" if item.page < page else "➡️", callback_data=item.pack()))
    if row:
        builder.row(*row)
    await answer(event, format_listing_card(listing, i18n), parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(PageCB.filter(F.scope == "favorites"))
async def favorites_page(callback: CallbackQuery, callback_data: PageCB, session, user, i18n: I18n) -> None:
    await render_favorites(callback, session, user.id, i18n, callback_data.page)
    await callback.answer()


@router.callback_query(FavCB.filter(F.action == "unfav"))
async def remove_from_favorites(
    callback: CallbackQuery, callback_data: FavCB, session, user, i18n: I18n, state
) -> None:
    await interactions.remove_favorite(session, user.id, callback_data.id)
    current = await state.get_data()
    if current.get("current_listing_id") == callback_data.id and current.get("result_total"):
        from handlers.search import show_result

        await show_result(callback, state, session, i18n, current.get("current_page", 1), bot=callback.bot)
    else:
        await render_favorites(callback, session, user.id, i18n, 1)
    await callback.answer(i18n.t("favorites.removed"))
