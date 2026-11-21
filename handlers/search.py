from __future__ import annotations

from typing import Any

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import (
    ContactRequest,
    District,
    Listing,
    Neighborhood,
    PropertyType,
    Region,
)
from database.repositories import interactions, listings as listing_repo
from handlers.common import MenuTextFilter, StateDataHas, answer, require_user
from keyboards.inline import (
    CardCB,
    DealCB,
    DistrictCB,
    FavCB,
    FilterCB,
    NbhdCB,
    NavCB,
    PageCB,
    PropCB,
    ProfileCB,
    RegionCB,
    SavedCB,
    amenities_kb,
    back_button,
    bool_kb,
    choices_kb,
    commercial_deal_kb,
    condition_kb,
    districts_kb,
    filter_menu_kb,
    furnished_kb,
    listing_card_kb,
    neighborhoods_kb,
    property_type_kb,
    regions_kb,
    renovation_kb,
    report_reasons_kb,
    results_nav_kb,
    saved_search_kb,
    search_deal_kb,
    utilities_kb,
)
from keyboards.reply import skip_kb
from services.search_service import normalize_filters, search_page, serialize_filters
from states.profile import CommonFlow
from states.search import SearchFlow
from utils.formatters import format_listing_card, format_price, summarize_filters
from utils.i18n import I18n
from utils.pagination import SEARCH_PAGE_SIZE

router = Router(name="search")

NUMERIC_STATES = {
    SearchFlow.rooms: ("rooms", "search.ask_rooms"),
    SearchFlow.floor: ("floor", "search.ask_floor"),
    SearchFlow.guests: ("guests", "search.ask_guests"),
}


async def get_regions(session: AsyncSession) -> list[Region]:
    result = await session.execute(select(Region).where(Region.is_active.is_(True)).order_by(Region.id))
    return list(result.scalars().all())


async def get_districts(session: AsyncSession, region_id: int) -> list[District]:
    result = await session.execute(
        select(District).where(District.region_id == region_id, District.is_active.is_(True)).order_by(District.id)
    )
    return list(result.scalars().all())


async def get_neighborhoods(session: AsyncSession, district_id: int) -> list[Neighborhood]:
    result = await session.execute(
        select(Neighborhood).where(Neighborhood.district_id == district_id).order_by(Neighborhood.id)
    )
    return list(result.scalars().all())


async def get_property_types(session: AsyncSession) -> list[PropertyType]:
    result = await session.execute(
        select(PropertyType).where(PropertyType.is_active.is_(True)).order_by(PropertyType.sort_order)
    )
    return list(result.scalars().all())


@router.message(MenuTextFilter("menu.search"))
async def open_search(message: Message, user: object | None, i18n: I18n) -> None:
    if not await require_user(message, user, i18n):
        return
    await message.answer(i18n.t("search.title"), reply_markup=search_deal_kb(i18n))


@router.callback_query(NavCB.filter(F.action == "search"))
async def nav_search(callback: CallbackQuery, user: object | None, i18n: I18n) -> None:
    if not await require_user(callback, user, i18n):
        await callback.answer()
        return
    await answer(callback, i18n.t("search.title"), reply_markup=search_deal_kb(i18n))
    await callback.answer()


@router.callback_query(StateFilter(None), DealCB.filter())
async def choose_deal(
    callback: CallbackQuery,
    callback_data: DealCB,
    state,
    session: AsyncSession,
    user: object | None,
    i18n: I18n,
) -> None:
    if not await require_user(callback, user, i18n):
        await callback.answer()
        return
    if callback_data.value == "COMMERCIAL":
        await state.set_state(SearchFlow.deal_type)
        await answer(callback, i18n.t("search.ask_deal_type"), reply_markup=commercial_deal_kb(i18n))
        await callback.answer()
        return
    await state.set_data({"listing_type": callback_data.value, "sort": "new"})
    await state.set_state(SearchFlow.property_type)
    await answer(
        callback,
        i18n.t("search.select_property_type"),
        reply_markup=property_type_kb(i18n, await get_property_types(session)),
    )
    await callback.answer()


@router.callback_query(SearchFlow.deal_type, DealCB.filter())
async def choose_commercial_deal(
    callback: CallbackQuery, callback_data: DealCB, state, session: AsyncSession, i18n: I18n
) -> None:
    await state.set_data({"listing_type": callback_data.value, "sort": "new"})
    await state.set_state(SearchFlow.property_type)
    await answer(
        callback,
        i18n.t("search.select_property_type"),
        reply_markup=property_type_kb(i18n, await get_property_types(session)),
    )
    await callback.answer()


@router.callback_query(SearchFlow.property_type, PropCB.filter())
async def choose_property(
    callback: CallbackQuery, callback_data: PropCB, state, session: AsyncSession, i18n: I18n
) -> None:
    data = await state.get_data()
    data["property_type_id"] = callback_data.id
    data["property_type_code"] = callback_data.code
    await state.set_data(data)
    await state.set_state(SearchFlow.region)
    await answer(callback, i18n.t("search.select_region"), reply_markup=regions_kb(i18n, await get_regions(session)))
    await callback.answer()


@router.callback_query(SearchFlow.region, RegionCB.filter())
async def choose_region(
    callback: CallbackQuery, callback_data: RegionCB, state, session: AsyncSession, i18n: I18n
) -> None:
    await callback.answer()
    regions = await get_regions(session)
    region = next((r for r in regions if r.id == callback_data.id), None)
    markup = districts_kb(i18n, await get_districts(session, callback_data.id))
    data = await state.get_data()
    data["region_id"] = callback_data.id
    data["region_name"] = (
        getattr(region, f"name_{i18n.lang}", None) or region.name_uz if region else ""
    )
    await state.set_data(data)
    await state.set_state(SearchFlow.district)
    await answer(callback, i18n.t("search.select_district"), reply_markup=markup)


@router.callback_query(SearchFlow.district, NavCB.filter(F.action == "regions"))
async def back_to_search_regions(
    callback: CallbackQuery, state, session: AsyncSession, i18n: I18n
) -> None:
    await callback.answer()
    await state.set_state(SearchFlow.region)
    await answer(
        callback,
        i18n.t("search.select_region"),
        reply_markup=regions_kb(i18n, await get_regions(session), scope="search"),
    )


@router.callback_query(SearchFlow.district, FilterCB.filter(F.action == "skip_district"))
async def skip_district(
    callback: CallbackQuery, state, session: AsyncSession, i18n: I18n, user: object | None
) -> None:
    await callback.answer()
    data = await state.get_data()
    for key in ("district_id", "district_name", "neighborhood_id"):
        data.pop(key, None)
    await state.set_data(data)
    await state.set_state(SearchFlow.results)
    await show_result(callback, state, session, i18n, 1, bot=callback.bot, user=user)


@router.callback_query(SearchFlow.district, DistrictCB.filter())
async def choose_district(
    callback: CallbackQuery, callback_data: DistrictCB, state, session: AsyncSession, i18n: I18n
) -> None:
    data = await state.get_data()
    data["district_id"] = callback_data.id
    districts = await get_districts(session, data["region_id"])
    district = next((d for d in districts if d.id == callback_data.id), None)
    data["district_name"] = (
        getattr(district, f"name_{i18n.lang}", None) or district.name_uz if district else ""
    )
    await state.set_data(data)
    await state.set_state(SearchFlow.neighborhood)
    await answer(
        callback,
        i18n.t("search.select_neighborhood"),
        reply_markup=neighborhoods_kb(i18n, await get_neighborhoods(session, callback_data.id)),
    )
    await callback.answer()


@router.callback_query(SearchFlow.neighborhood, FilterCB.filter(F.action == "skip_nbhd"))
@router.callback_query(SearchFlow.neighborhood, NbhdCB.filter())
async def finish_location(
    callback: CallbackQuery,
    state,
    session: AsyncSession,
    i18n: I18n,
    user: object | None,
    callback_data: NbhdCB | None = None,
) -> None:
    await callback.answer()
    if isinstance(callback_data, NbhdCB):
        data = await state.get_data()
        data["neighborhood_id"] = callback_data.id
        await state.set_data(data)
    await state.set_state(SearchFlow.results)
    await show_result(callback, state, session, i18n, 1, bot=callback.bot, user=user)


FILTER_STATE_MAP = {
    "rooms": SearchFlow.rooms,
    "floor": SearchFlow.floor,
    "guests": SearchFlow.guests,
}

CATEGORICAL_MAP = {
    "condition": "condition",
    "renovation": "renovation",
    "furnished": "furnished",
    "family": "is_family_allowed",
    "students": "is_student_allowed",
    "long_term": "is_long_term",
    "deposit": "has_deposit",
    "utilities": "utilities_terms",
}


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action.in_(list(FILTER_STATE_MAP.keys()))))
async def ask_numeric_filter(
    callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n
) -> None:
    field = callback_data.action
    await state.set_state(FILTER_STATE_MAP[field])
    prompt_key = dict((v[0], v[1]) for v in NUMERIC_STATES.values())[field]
    await answer(callback, i18n.t(prompt_key), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.message(StateFilter(*NUMERIC_STATES))
async def save_numeric_filter(message: Message, state, i18n: I18n) -> None:
    current = await state.get_state()
    field, _ = NUMERIC_STATES[current]
    data = await state.get_data()
    if message.text == i18n.t("common.skip"):
        data.pop(field, None)
    else:
        from utils.validators import parse_int, parse_int_list

        if field == "rooms":
            value = parse_int_list(message.text)
        else:
            value = parse_int(message.text)
        if not value:
            await message.answer(i18n.t("listing.invalid_number"), reply_markup=skip_kb(i18n))
            return
        data[field] = value
    await state.set_data(data)
    await state.set_state(SearchFlow.results)
    await message.answer(i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, data))


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "condition"))
async def choose_condition(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("search.ask_condition"), reply_markup=condition_kb(i18n))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "renovation"))
async def choose_renovation(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("search.ask_renovation"), reply_markup=renovation_kb(i18n))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "furnished"))
async def choose_furnished(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("search.ask_furnished"), reply_markup=furnished_kb(i18n))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action.in_(["family", "students", "long_term", "deposit"])))
async def choose_bool_filter(callback: CallbackQuery, callback_data: FilterCB, i18n: I18n) -> None:
    key_map = {
        "family": "search.ask_family",
        "students": "search.ask_students",
        "long_term": "search.ask_long_term",
        "deposit": "search.ask_deposit",
    }
    await answer(callback, i18n.t(key_map[callback_data.action]), reply_markup=bool_kb(i18n, callback_data.action))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "utilities"))
async def choose_utilities(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("search.ask_utilities"), reply_markup=utilities_kb(i18n))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action.in_(list(CATEGORICAL_MAP.keys()) + ["skip"])))
async def save_categorical_filter(
    callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    if callback_data.action == "skip":
        pass
    else:
        key = CATEGORICAL_MAP[callback_data.action]
        value: Any = callback_data.value
        if value in {"0", "1"}:
            value = bool(int(value))
        data[key] = value
    await state.set_data(data)
    await state.set_state(SearchFlow.results)
    await answer(callback, i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, data))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "amenity"))
async def toggle_amenity(callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n) -> None:
    data = await state.get_data()
    selected = list(data.get("amenities") or [])
    if callback_data.value in selected:
        selected.remove(callback_data.value)
    else:
        selected.append(callback_data.value)
    data["amenities"] = selected
    await state.set_data(data)
    try:
        await callback.message.edit_reply_markup(reply_markup=amenities_kb(i18n, selected))
    except Exception:
        pass
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "amenities_done"))
async def amenities_done(callback: CallbackQuery, state, i18n: I18n) -> None:
    await state.set_state(SearchFlow.results)
    await answer(callback, i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, await state.get_data()))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "sort"))
async def set_sort(callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n) -> None:
    data = await state.get_data()
    data["sort"] = callback_data.value
    await state.set_data(data)
    await answer(callback, i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, data))
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "by_title"))
async def ask_title(callback: CallbackQuery, state, i18n: I18n) -> None:
    await state.set_state(SearchFlow.title)
    await answer(callback, i18n.t("search.ask_title"), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.message(SearchFlow.title)
async def save_title(message: Message, state, i18n: I18n) -> None:
    data = await state.get_data()
    if message.text != i18n.t("common.skip"):
        data["query"] = message.text[:128]
    await state.set_data(data)
    await state.set_state(SearchFlow.results)
    await message.answer(i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, data))


@router.callback_query(FilterCB.filter(F.action == "quick"))
async def quick_search(
    callback: CallbackQuery, callback_data: FilterCB, state, session: AsyncSession, i18n: I18n, user: object
) -> None:
    data = {"sort": callback_data.value}
    await state.set_data(data)
    await state.set_state(SearchFlow.results)
    await show_result(callback, state, session, i18n, 1, bot=callback.bot, user=user)
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "show"))
async def show_search_results(
    callback: CallbackQuery, state, session: AsyncSession, i18n: I18n, user: object
) -> None:
    await state.set_state(SearchFlow.results)
    await show_result(callback, state, session, i18n, 1, bot=callback.bot, user=user)
    await callback.answer()


@router.callback_query(NavCB.filter(F.action == "search_filters"))
async def back_to_filters(callback: CallbackQuery, state, i18n: I18n) -> None:
    data = await state.get_data()
    await state.set_state(SearchFlow.results)
    await answer(callback, i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, data))
    await callback.answer()


async def show_result(
    event,
    state,
    session: AsyncSession,
    i18n: I18n,
    page: int,
    bot: Bot | None,
    user: object | None = None,
) -> None:
    from utils.pagination import normalize_page

    data = await state.get_data()
    filters = normalize_filters(data)
    items, total = await search_page(session, filters, page, user_id=user.id if user else None)
    page = normalize_page(page, total, SEARCH_PAGE_SIZE)
    if total == 0 or not items:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=i18n.t("search.change_filters"),
            callback_data=NavCB(action="search_filters").pack(),
        )
        builder.button(
            text=i18n.t("common.main_menu"),
            callback_data=NavCB(action="main").pack(),
        )
        await answer(event, i18n.t("search.no_results"), reply_markup=builder.as_markup())
        return

    listing = items[0]
    is_fav = await interactions.is_favorite(session, user.id, listing.id) if user else False
    caption = format_listing_card(listing, i18n)
    markup = listing_card_kb(i18n, listing.id, page, is_fav)
    data["current_listing_id"] = listing.id
    data["current_page"] = page
    data["result_total"] = total
    await state.set_data(data)

    primary = next((image for image in listing.images if image.is_primary), None) or (
        listing.images[0] if listing.images else None
    )
    message = None
    if primary and bot:
        try:
            message = await bot.send_photo(
                chat_id=event.from_user.id,
                photo=primary.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup,
            )
        except Exception:
            message = None
    if message is None:
        await answer(event, caption, reply_markup=markup)

    nav_markup = results_nav_kb(i18n, page, total)
    await answer(event, i18n.t("search.results_title", count=total), reply_markup=nav_markup)
    await listing_repo.increment_views(session, listing.id)


@router.callback_query(PageCB.filter(F.scope == "results"))
async def paginate_results(
    callback: CallbackQuery, callback_data: PageCB, state, session: AsyncSession, i18n: I18n, user: object
) -> None:
    await show_result(callback, state, session, i18n, callback_data.page, bot=callback.bot, user=user)
    await callback.answer()


@router.callback_query(StateDataHas("current_listing_id"), FavCB.filter(F.action.in_(["fav", "unfav"])))
async def toggle_favorite(
    callback: CallbackQuery, callback_data: FavCB, state, session: AsyncSession, i18n: I18n, user: object
) -> None:
    user_id = user.id
    if callback_data.action == "fav":
        added = await interactions.add_favorite(session, user_id, callback_data.id)
        text = i18n.t("favorites.added") if added else i18n.t("favorites.removed")
    else:
        await interactions.remove_favorite(session, user_id, callback_data.id)
        text = i18n.t("favorites.removed")
    data = await state.get_data()
    await state.set_data(data)
    await show_result(callback, state, session, i18n, data.get("current_page", callback_data.page), bot=callback.bot, user=user)
    await callback.answer(text)


@router.callback_query(CardCB.filter(F.action == "contact"))
async def start_contact(
    callback: CallbackQuery, callback_data: CardCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    data["inquiry_listing_id"] = callback_data.id
    await state.set_data(data)
    await state.set_state(CommonFlow.inquiry_name)
    await answer(callback, i18n.t("inquiry.ask_name"), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.callback_query(CardCB.filter(F.action == "viewing"))
async def start_viewing(
    callback: CallbackQuery, callback_data: CardCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    data["viewing_listing_id"] = callback_data.id
    await state.set_data(data)
    await state.set_state(CommonFlow.viewing_date)
    await answer(callback, i18n.t("viewing.ask_date"), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.callback_query(CardCB.filter(F.action == "report"))
async def start_report(
    callback: CallbackQuery, callback_data: CardCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    data["report_listing_id"] = callback_data.id
    await state.set_data(data)
    await answer(callback, i18n.t("report.title"), reply_markup=report_reasons_kb(i18n, callback_data.id))
    await callback.answer()


@router.callback_query(FilterCB.filter(F.action == "report_reason"))
async def save_report_reason(
    callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    data["report_reason"] = callback_data.value
    await state.set_data(data)
    await state.set_state(CommonFlow.report_details)
    await answer(callback, i18n.t("report.ask_details"), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.callback_query(CardCB.filter(F.action.in_(["share", "photo", "back"])))
async def card_extra(
    callback: CallbackQuery, callback_data: CardCB, state, session: AsyncSession, i18n: I18n, user: object
) -> None:
    data = await state.get_data()
    listing = await listing_repo.get(session, data.get("current_listing_id", callback_data.id))
    if not listing:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    if callback_data.action == "share":
        text = i18n.t(
            "listing_card.share_text",
            title=listing.title,
            region=listing.region.name_uz if listing.region else "—",
            price=format_price(listing.price, i18n),
        )
        await answer(callback, text)
    elif callback_data.action == "photo":
        for image in listing.images:
            try:
                await callback.bot.send_photo(chat_id=callback.from_user.id, photo=image.file_id)
            except Exception:
                pass
    else:
        await show_result(callback, state, session, i18n, data.get("current_page", 1), bot=callback.bot, user=user)
    await callback.answer()


@router.callback_query(SearchFlow.results, FilterCB.filter(F.action == "save"))
async def save_search(callback: CallbackQuery, state, i18n: I18n) -> None:
    await state.set_state(CommonFlow.saved_search_name)
    await answer(callback, i18n.t("saved_search.ask_name"), reply_markup=skip_kb(i18n))
    await callback.answer()


@router.message(CommonFlow.saved_search_name)
async def confirm_saved_search(
    message: Message, state, session: AsyncSession, user: object, i18n: I18n
) -> None:
    data = await state.get_data()
    name = message.text if message.text != i18n.t("common.skip") else summarize_filters(data, i18n)
    await interactions.create_saved_search(
        session, user.id, name[:128], serialize_filters(data)
    )
    await state.set_state(SearchFlow.results)
    await message.answer(i18n.t("search.saved"))
    await message.answer(i18n.t("search.filters_title"), reply_markup=filter_menu_kb(i18n, data))


@router.callback_query(SavedCB.filter())
async def saved_search_actions(
    callback: CallbackQuery,
    callback_data: SavedCB,
    state,
    session: AsyncSession,
    user: object,
    i18n: I18n,
) -> None:
    item = await interactions.get_saved_search(session, callback_data.id)
    if not item:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    if callback_data.action == "delete":
        await interactions.delete_saved_search(session, item.id)
        text = i18n.t("saved_search.deleted")
    else:
        item.notify = not item.notify
        text = i18n.t("saved_search.toggled_on" if item.notify else "saved_search.toggled_off")
    await callback.answer(text)
    from handlers.profile import show_saved_searches

    await show_saved_searches(callback, session, user, i18n)
