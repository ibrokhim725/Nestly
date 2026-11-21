from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery, Location, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Listing, ListingStatus
from database.repositories import listings as listing_repo
from handlers.common import MenuTextFilter, StateIn, answer, require_user
from handlers.search import (
    get_districts,
    get_neighborhoods,
    get_property_types,
    get_regions,
)
from keyboards.inline import (
    ConfirmCB,
    DealCB,
    DistrictCB,
    FilterCB,
    ImgCB,
    MyListCB,
    NbhdCB,
    NavCB,
    PropCB,
    RegionCB,
    bool_kb,
    condition_kb,
    confirm_delete_kb,
    districts_kb,
    edit_fields_kb,
    furnished_kb,
    image_index_kb,
    images_kb,
    my_listing_manage_kb,
    my_listings_kb,
    neighborhoods_kb,
    post_type_kb,
    preview_kb,
    price_unit_kb,
    property_type_kb,
    regions_kb,
    renovation_kb,
    utilities_kb,
    video_kb,
)
from keyboards.reply import location_kb, main_menu_kb, skip_kb
from services.listing_service import build_title, format_preview, submit_listing
from services.moderation_service import change_status
from states.listing import EditListing, NewListing
from utils.formatters import format_full_listing
from utils.i18n import I18n
from utils.validators import (
    clean_text,
    is_valid_phone,
    is_valid_year,
    normalize_phone,
    parse_decimal,
    parse_int,
)

router = Router(name="listing")

RENT_TYPES = {"RENT", "DAILY", "COMMERCIAL_RENT"}

INPUT_FIELDS: list[tuple[Any, str, str, str]] = [
    (NewListing.area, "area", "listing.ask_area", "decimal"),
    (NewListing.rooms, "rooms", "listing.ask_rooms", "int"),
    (NewListing.floor, "floor", "listing.ask_floor", "int"),
    (NewListing.total_floors, "total_floors", "listing.ask_total_floors", "int"),
    (NewListing.built_year, "built_year", "listing.ask_built_year", "year"),
    (NewListing.description, "description", "listing.ask_description", "text"),
    (NewListing.price, "price", "listing.ask_price", "decimal"),
    (NewListing.contact_phone, "contact_phone", "listing.ask_phone", "phone"),
    (NewListing.extra, "extra", "listing.ask_extra", "text"),
]

RENT_FIELDS: list[tuple[Any, str, str, str]] = [
    (NewListing.family, "is_family_allowed", "listing.ask_family", "bool"),
    (NewListing.students, "is_student_allowed", "listing.ask_students", "bool"),
    (NewListing.long_term, "is_long_term", "listing.ask_long_term", "bool"),
    (NewListing.deposit, "has_deposit", "listing.ask_deposit", "bool"),
    (NewListing.utilities, "utilities_terms", "listing.ask_utilities", "choice"),
    (NewListing.guests, "guests", "listing.ask_guests", "int"),
]

CHOICE_STATES = {
    NewListing.condition: ("condition", "condition"),
    NewListing.renovation: ("renovation", "renovation"),
    NewListing.furnished: ("furnished", "furnished"),
    NewListing.price_unit: ("price_unit", "price_unit"),
    NewListing.utilities: ("utilities_terms", "new_utilities"),
    NewListing.family: ("is_family_allowed", "new_family"),
    NewListing.students: ("is_student_allowed", "new_students"),
    NewListing.long_term: ("is_long_term", "new_long_term"),
    NewListing.deposit: ("has_deposit", "new_deposit"),
}


def field_sequence(data: dict[str, Any]) -> list[tuple[Any, str, str, str]]:
    fields = list(INPUT_FIELDS[:5])
    fields += [
        (NewListing.condition, "condition", "listing.ask_condition", "choice"),
        (NewListing.renovation, "renovation", "listing.ask_renovation", "choice"),
        (NewListing.furnished, "furnished", "listing.ask_furnished", "choice"),
    ]
    fields += INPUT_FIELDS[5:7]
    fields += [(NewListing.price_unit, "price_unit", "listing.ask_price_unit", "choice")]
    fields += INPUT_FIELDS[7:]
    if str(data.get("listing_type", "")) in RENT_TYPES:
        fields += RENT_FIELDS
    return fields


async def ask_field(event, state, i18n: I18n, session: AsyncSession) -> None:
    data = await state.get_data()
    sequence = field_sequence(data)
    for field_state, key, prompt, kind in sequence:
        if key in data:
            continue
        await state.set_state(field_state)
        markup = None
        if kind == "choice":
            markup = choice_markup(key, i18n)
        elif kind == "text" and key == "extra":
            markup = skip_kb(i18n)
        elif key == "contact_phone":
            builder = InlineKeyboardBuilder()
            builder.button(
                text=i18n.t("listing.use_profile_phone"),
                callback_data=FilterCB(action="use_profile_phone").pack(),
            )
            markup = builder.as_markup()
        await answer(event, i18n.t(prompt), reply_markup=markup)
        return
    await state.set_state(NewListing.location)
    await answer(event, i18n.t("listing.ask_location"), reply_markup=location_kb(i18n))


def choice_markup(key: str, i18n: I18n):
    mapping = {
        "condition": condition_kb(i18n),
        "renovation": renovation_kb(i18n),
        "furnished": furnished_kb(i18n),
        "price_unit": price_unit_kb(i18n),
        "utilities_terms": utilities_kb(i18n, "new_utilities"),
        "is_family_allowed": bool_kb(i18n, "new_family"),
        "is_student_allowed": bool_kb(i18n, "new_students"),
        "is_long_term": bool_kb(i18n, "new_long_term"),
        "has_deposit": bool_kb(i18n, "new_deposit"),
    }
    return mapping.get(key)


@router.message(MenuTextFilter("menu.post"))
async def start_post(message: Message, session: AsyncSession, user: object, i18n: I18n, state) -> None:
    if not await require_user(message, user, i18n):
        return
    count = await listing_repo.count_by_user_and_status(session, user.id, ListingStatus.ACTIVE)
    if count >= settings.max_active_listings_per_user:
        await message.answer(i18n.t("listing.no_active_limit", limit=settings.max_active_listings_per_user))
        return
    await state.clear()
    await state.set_state(NewListing.listing_type)
    await message.answer(i18n.t("listing.ask_type"), reply_markup=post_type_kb(i18n))


@router.callback_query(NewListing.listing_type, DealCB.filter())
async def choose_post_type(
    callback: CallbackQuery, callback_data: DealCB, state, i18n: I18n, session: AsyncSession
) -> None:
    data = {"listing_type": callback_data.value}
    await state.set_data(data)
    await state.set_state(NewListing.property_type)
    await answer(
        callback,
        i18n.t("listing.select_property_type"),
        reply_markup=property_type_kb(i18n, await get_property_types(session), scope="cancel"),
    )
    await callback.answer()


@router.callback_query(NewListing.property_type, PropCB.filter())
async def choose_post_property(
    callback: CallbackQuery, callback_data: PropCB, state, session: AsyncSession, i18n: I18n
) -> None:
    data = await state.get_data()
    data["property_type_id"] = callback_data.id
    data["property_type_code"] = callback_data.code
    await state.set_data(data)
    await state.set_state(NewListing.region)
    await answer(callback, i18n.t("listing.select_region"), reply_markup=regions_kb(i18n, await get_regions(session), scope="cancel"))
    await callback.answer()


@router.callback_query(NewListing.region, RegionCB.filter())
async def choose_post_region(
    callback: CallbackQuery, callback_data: RegionCB, state, session: AsyncSession, i18n: I18n
) -> None:
    await callback.answer()
    regions = await get_regions(session)
    region = next((r for r in regions if r.id == callback_data.id), None)
    markup = districts_kb(i18n, await get_districts(session, callback_data.id), scope="cancel")
    data = await state.get_data()
    data["region_id"] = callback_data.id
    data["region_name"] = getattr(region, f"name_{i18n.lang}", None) or region.name_uz if region else ""
    await state.set_data(data)
    await state.set_state(NewListing.district)
    await answer(callback, i18n.t("listing.select_district"), reply_markup=markup)


@router.callback_query(StateIn([NewListing.district]), NavCB.filter(F.action == "regions"))
async def back_to_post_regions(
    callback: CallbackQuery, state, session: AsyncSession, i18n: I18n
) -> None:
    await callback.answer()
    await state.set_state(NewListing.region)
    await answer(
        callback,
        i18n.t("listing.select_region"),
        reply_markup=regions_kb(i18n, await get_regions(session), scope="cancel"),
    )


@router.callback_query(NewListing.district, DistrictCB.filter())
async def choose_post_district(
    callback: CallbackQuery, callback_data: DistrictCB, state, session: AsyncSession, i18n: I18n
) -> None:
    data = await state.get_data()
    data["district_id"] = callback_data.id
    districts = await get_districts(session, data["region_id"])
    district = next((d for d in districts if d.id == callback_data.id), None)
    data["district_name"] = getattr(district, f"name_{i18n.lang}", None) or district.name_uz if district else ""
    await state.set_data(data)
    await state.set_state(NewListing.neighborhood)
    await answer(callback, i18n.t("listing.select_neighborhood"), reply_markup=neighborhoods_kb(i18n, await get_neighborhoods(session, callback_data.id)))
    await callback.answer()


@router.callback_query(NewListing.neighborhood, FilterCB.filter(F.action == "skip_nbhd"))
@router.callback_query(NewListing.neighborhood, NbhdCB.filter())
async def choose_post_neighborhood(
    callback: CallbackQuery,
    state,
    i18n: I18n,
    session: AsyncSession,
    callback_data: NbhdCB | None = None,
) -> None:
    if isinstance(callback_data, NbhdCB):
        data = await state.get_data()
        data["neighborhood_id"] = callback_data.id
        await state.set_data(data)
    await ask_field(callback, state, i18n, session)
    await callback.answer()


@router.message(StateIn([item[0] for item in INPUT_FIELDS]))
async def collect_input(message: Message, state, i18n: I18n, session: AsyncSession, user: object) -> None:
    current = await state.get_state()
    field = next((item for item in INPUT_FIELDS if item[0] == current), None)
    if not field:
        return
    _, key, prompt, kind = field
    data = await state.get_data()

    if message.text == i18n.t("common.cancel"):
        await state.clear()
        await message.answer(i18n.t("listing.cancelled"), reply_markup=main_menu_kb(i18n))
        return
    if key == "extra" and message.text == i18n.t("common.skip"):
        data[key] = ""
        await state.set_data(data)
        await ask_field(message, state, i18n, session)
        return

    text = message.text or ""
    value: Any = None
    if kind == "decimal":
        value = parse_decimal(text)
        if value is None:
            await message.answer(i18n.t("listing.invalid_price") if key == "price" else i18n.t("listing.invalid_area"))
            return
        value = float(value)
    elif kind == "int":
        value = parse_int(text)
        if value is None or value < 0:
            await message.answer(i18n.t("listing.invalid_number"))
            return
    elif kind == "year":
        value = parse_int(text)
        if not is_valid_year(value):
            await message.answer(i18n.t("listing.invalid_year"))
            return
    elif kind == "phone":
        if not is_valid_phone(text):
            await message.answer(i18n.t("registration.phone_invalid"))
            return
        value = normalize_phone(text)
    else:
        value = clean_text(text, 2000)

    data[key] = value
    await state.set_data(data)
    await ask_field(message, state, i18n, session)


@router.callback_query(FilterCB.filter(F.action == "use_profile_phone"))
async def use_profile_phone(
    callback: CallbackQuery, state, user: object, i18n: I18n, session: AsyncSession
) -> None:
    data = await state.get_data()
    data["contact_phone"] = user.phone
    await state.set_data(data)
    await ask_field(callback, state, i18n, session)
    await callback.answer()


@router.callback_query(StateIn(CHOICE_STATES.keys()), FilterCB.filter())
async def collect_choice(
    callback: CallbackQuery,
    state,
    i18n: I18n,
    session: AsyncSession,
    callback_data: FilterCB | None = None,
) -> None:
    current = await state.get_state()
    if current not in CHOICE_STATES:
        await callback.answer()
        return
    key, action = CHOICE_STATES[current]
    if callback_data is None or (callback_data.action not in {action, "skip", ""}):
        await callback.answer()
        return
    data = await state.get_data()
    if callback_data.action == "skip":
        data[key] = None
    elif callback_data.value in {"0", "1"}:
        data[key] = bool(int(callback_data.value))
    elif current == NewListing.price_unit:
        data[key] = callback_data.value
    else:
        data[key] = callback_data.value
    await state.set_data(data)
    await ask_field(callback, state, i18n, session)
    await callback.answer()


@router.message(NewListing.location)
async def get_location(message: Message, state, session: AsyncSession, i18n: I18n, user: object) -> None:
    data = await state.get_data()
    if message.text == i18n.t("common.skip"):
        data["latitude"] = None
        data["longitude"] = None
    elif isinstance(message.location, Location):
        data["latitude"] = message.location.latitude
        data["longitude"] = message.location.longitude
    else:
        await message.answer(i18n.t("listing.ask_location"), reply_markup=location_kb(i18n))
        return
    await state.set_data(data)
    listing = await submit_listing(
        session, user.id, data, i18n, status=ListingStatus.DRAFT
    )
    if listing is None:
        await message.answer(i18n.t("common.error"))
        return
    data["draft_listing_id"] = listing.id
    await state.set_data(data)
    await state.set_state(NewListing.images)
    await message.answer(
        i18n.t("listing.upload_images", min=settings.min_listing_images, max=settings.max_listing_images),
        reply_markup=images_kb(i18n, 0, settings.min_listing_images),
    )


@router.message(NewListing.images, F.photo)
async def collect_image(message: Message, state, session: AsyncSession, i18n: I18n) -> None:
    data = await state.get_data()
    listing = await listing_repo.get(session, data["draft_listing_id"])
    if not listing:
        await message.answer(i18n.t("common.error"))
        return
    if len(listing.images) >= settings.max_listing_images:
        await message.answer(i18n.t("listing.max_images_error", max=settings.max_listing_images))
        return
    await listing_repo.add_image(session, listing.id, message.photo[-1].file_id, len(listing.images))
    await message.answer(
        i18n.t("listing.images_received", count=len(listing.images) + 1),
        reply_markup=images_kb(i18n, len(listing.images) + 1, settings.min_listing_images),
    )


@router.callback_query(NewListing.images, ImgCB.filter(F.action.in_(["primary_menu", "delete_menu", "move_menu"])))
async def image_menu(
    callback: CallbackQuery, callback_data: ImgCB, state, session: AsyncSession, i18n: I18n
) -> None:
    data = await state.get_data()
    listing = await listing_repo.get(session, data["draft_listing_id"])
    if not listing or not listing.images:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    action = {
        "primary_menu": "set_primary",
        "delete_menu": "delete_image",
        "move_menu": "move_image",
    }[callback_data.action]
    await answer(callback, "👇", reply_markup=image_index_kb(i18n, listing.images, action))
    await callback.answer()


@router.callback_query(NewListing.images, ImgCB.filter(F.action == "images_back"))
async def images_back(callback: CallbackQuery, state, session: AsyncSession, i18n: I18n) -> None:
    data = await state.get_data()
    listing = await listing_repo.get(session, data["draft_listing_id"])
    count = len(listing.images) if listing else 0
    await answer(callback, i18n.t("listing.upload_images", min=settings.min_listing_images, max=settings.max_listing_images), reply_markup=images_kb(i18n, count, settings.min_listing_images))
    await callback.answer()


@router.callback_query(NewListing.images, ImgCB.filter(F.action.in_(["set_primary", "delete_image", "move_image"])))
async def manage_image(
    callback: CallbackQuery, callback_data: ImgCB, state, session: AsyncSession, i18n: I18n
) -> None:
    data = await state.get_data()
    listing = await listing_repo.get(session, data["draft_listing_id"])
    if not listing:
        await callback.answer(i18n.t("common.not_found"), show_alert=True)
        return
    action = callback_data.action
    if action == "set_primary":
        await listing_repo.set_primary_image(session, listing.id, callback_data.id)
        text = i18n.t("listing.primary_set")
    elif action == "delete_image":
        await listing_repo.delete_image(session, callback_data.id)
        text = i18n.t("listing.image_deleted")
    else:
        await listing_repo.move_image(session, callback_data.id, 1)
        text = i18n.t("common.done")
    listing = await listing_repo.get(session, data["draft_listing_id"])
    count = len(listing.images) if listing else 0
    await answer(callback, text, reply_markup=images_kb(i18n, count, settings.min_listing_images))
    await callback.answer()


@router.callback_query(NewListing.images, ConfirmCB.filter(F.action == "images_done"))
async def finish_images(callback: CallbackQuery, state, session: AsyncSession, i18n: I18n) -> None:
    data = await state.get_data()
    listing = await listing_repo.get(session, data["draft_listing_id"])
    if not listing or len(listing.images) < settings.min_listing_images:
        await callback.answer(
            i18n.t("listing.min_images_error", min=settings.min_listing_images), show_alert=True
        )
        return
    await state.set_state(NewListing.video)
    await answer(callback, i18n.t("listing.upload_video"), reply_markup=video_kb(i18n))
    await callback.answer()


@router.callback_query(NewListing.video, ConfirmCB.filter(F.action.in_(["video_yes", "video_no"])))
async def choose_video(callback: CallbackQuery, callback_data: ConfirmCB, state, i18n: I18n) -> None:
    if callback_data.action == "video_no":
        await preview_listing(callback, state, i18n, None)
    else:
        await state.set_state(NewListing.images)
        data = await state.get_data()
        data["_awaiting_video"] = True
        await state.set_data(data)
        await answer(callback, "🎬", reply_markup=skip_kb(i18n))
    await callback.answer()


@router.message(NewListing.images, F.video)
async def collect_video(message: Message, state, session: AsyncSession, i18n: I18n) -> None:
    data = await state.get_data()
    if not data.get("_awaiting_video"):
        await message.answer(i18n.t("listing.not_video"))
        return
    listing = await listing_repo.get_simple(session, data["draft_listing_id"])
    await listing_repo.add_video(session, listing.id, message.video.file_id)
    data.pop("_awaiting_video", None)
    await state.set_data(data)
    await preview_listing(message, state, i18n, session)


@router.message(NewListing.images)
async def media_warning(message: Message, state, i18n: I18n) -> None:
    data = await state.get_data()
    if data.get("_awaiting_video"):
        if message.text == i18n.t("common.skip"):
            data.pop("_awaiting_video", None)
            await state.set_data(data)
            await preview_listing(message, state, i18n, None)
        else:
            await message.answer(i18n.t("listing.not_video"))
    else:
        await message.answer(i18n.t("listing.not_photo"))


async def preview_listing(event, state, i18n: I18n, session: AsyncSession | None) -> None:
    data = await state.get_data()
    data.pop("_awaiting_video", None)
    await state.set_data(data)
    await state.set_state(NewListing.confirm)
    await answer(
        event,
        i18n.t("listing.preview", body=format_preview(data, i18n)),
        parse_mode="HTML",
        reply_markup=preview_kb(i18n),
    )


@router.callback_query(NewListing.confirm, ConfirmCB.filter(F.action == "send"))
async def send_listing(
    callback: CallbackQuery, state, session: AsyncSession, user: object, i18n: I18n
) -> None:
    data = await state.get_data()
    listing = await listing_repo.get_simple(session, data["draft_listing_id"])
    if not listing:
        await callback.answer(i18n.t("common.error"), show_alert=True)
        return
    listing.status = ListingStatus.PENDING
    listing.published_at = datetime.now(timezone.utc)
    listing.rejection_reason = None
    await state.clear()
    await answer(callback, i18n.t("listing.sent_for_moderation"), reply_markup=main_menu_kb(i18n))
    await callback.answer()


@router.callback_query(NewListing.confirm, ConfirmCB.filter(F.action == "cancel"))
async def cancel_listing(callback: CallbackQuery, state, session: AsyncSession, i18n: I18n) -> None:
    data = await state.get_data()
    listing = await listing_repo.get_simple(session, data.get("draft_listing_id", 0))
    if listing and listing.status == ListingStatus.DRAFT:
        await session.delete(listing)
    await state.clear()
    await answer(callback, i18n.t("listing.cancelled"), reply_markup=main_menu_kb(i18n))
    await callback.answer()


@router.callback_query(NewListing.confirm, ConfirmCB.filter(F.action == "edit"))
async def edit_listing(callback: CallbackQuery, state, i18n: I18n) -> None:
    await state.set_state(NewListing.edit_choice)
    await answer(callback, i18n.t("listing.edit_field"), reply_markup=edit_fields_kb(i18n))
    await callback.answer()


@router.callback_query(NewListing.edit_choice, FilterCB.filter(F.action == "edit_field"))
async def choose_edit_field(
    callback: CallbackQuery, callback_data: FilterCB, state, i18n: I18n
) -> None:
    data = await state.get_data()
    data["_edit_field"] = callback_data.value
    await state.set_data(data)
    await state.set_state(NewListing.edit_value)
    await answer(callback, i18n.t("listing.edit_field") + f": {callback_data.value}", reply_markup=skip_kb(i18n))
    await callback.answer()


@router.message(NewListing.edit_value)
async def apply_edit(message: Message, state, session: AsyncSession, i18n: I18n) -> None:
    data = await state.get_data()
    field = data.get("_edit_field")
    value: Any = message.text
    if field in {"price", "area", "rooms"}:
        parsed = parse_decimal(value) if field in {"price", "area"} else parse_int(value)
        if not parsed:
            await message.answer(i18n.t("listing.invalid_number"))
            return
        value = float(parsed)
    data[field] = value
    await state.set_data(data)
    await state.set_state(NewListing.confirm)
    await message.answer(i18n.t("profile.updated"))
    await message.answer(
        i18n.t("listing.preview", body=format_preview(data, i18n)),
        parse_mode="HTML",
        reply_markup=preview_kb(i18n),
    )


@router.callback_query(ConfirmCB.filter(F.action == "back_preview"))
async def back_preview(callback: CallbackQuery, state, i18n: I18n) -> None:
    await preview_listing(callback, state, i18n, None)
    await callback.answer()


# ---------------- My listings ----------------

@router.message(MenuTextFilter("menu.my_listings"))
async def my_listings_menu(message: Message, user: object | None, i18n: I18n) -> None:
    if not await require_user(message, user, i18n):
        return
    await message.answer(i18n.t("my_listings.title"), reply_markup=my_listings_kb(i18n))


STATUS_GROUPS = {
    "active": [ListingStatus.ACTIVE],
    "pending": [ListingStatus.PENDING],
    "rejected": [ListingStatus.REJECTED],
    "sold": [ListingStatus.SOLD],
    "rented": [ListingStatus.RENTED],
    "archived": [ListingStatus.ARCHIVED, ListingStatus.EXPIRED, ListingStatus.HIDDEN],
}


@router.callback_query(MyListCB.filter(F.action.in_(list(STATUS_GROUPS.keys()))))
async def list_my_listings(
    callback: CallbackQuery, callback_data: MyListCB, session: AsyncSession, user: object, i18n: I18n, state
) -> None:
    items = await listing_repo.list_by_user(session, user.id, STATUS_GROUPS[callback_data.action])
    if not items:
        await answer(callback, i18n.t("my_listings.empty"), reply_markup=my_listings_kb(i18n))
        await callback.answer()
        return
    await state.update_data(my_page=1, my_status=callback_data.action)
    await show_my_listing(callback, state, session, user, i18n, 1)


async def show_my_listing(event, state, session, user, i18n: I18n, page: int) -> None:
    from utils.pagination import normalize_page, paginate

    data = await state.get_data()
    items = await listing_repo.list_by_user(session, user.id, STATUS_GROUPS.get(data.get("my_status", "active"), []))
    page = normalize_page(page, len(items))
    listing = paginate(items, page, 1)[0]
    if not listing:
        await answer(event, i18n.t("my_listings.empty"), reply_markup=my_listings_kb(i18n))
        return
    data["my_current_id"] = listing.id
    data["my_page"] = page
    await state.set_data(data)
    caption = format_full_listing(listing, i18n)
    if listing.rejection_reason:
        caption += "\n\n" + i18n.t("my_listings.rejection_reason", reason=listing.rejection_reason)
    builder = InlineKeyboardBuilder()
    if page > 1:
        builder.button(text=i18n.t("common.prev"), callback_data=f"my_page:{page - 1}")
    builder.button(text=f"{page}/{len(items)}", callback_data="noop")
    if page < len(items):
        builder.button(text=i18n.t("common.next"), callback_data=f"my_page:{page + 1}")
    builder.adjust(3)
    await answer(event, caption, parse_mode="HTML", reply_markup=builder.as_markup())
    await answer(event, i18n.t("my_listings.manage"), reply_markup=my_listing_manage_kb(i18n, listing.id, listing.status.value))


@router.callback_query(F.data.startswith("my_page:"))
async def my_listing_page(callback: CallbackQuery, state, session: AsyncSession, user: object, i18n: I18n) -> None:
    page = int(callback.data.split(":")[1])
    await show_my_listing(callback, state, session, user, i18n, page)
    await callback.answer()


@router.callback_query(MyListCB.filter(F.action == "back"))
async def my_listings_back(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("my_listings.title"), reply_markup=my_listings_kb(i18n))
    await callback.answer()


@router.callback_query(MyListCB.filter(F.action.in_(["view", "refresh", "change_price", "hide", "unhide", "renew", "sold", "rented", "archive", "delete"])))
async def manage_my_listing(
    callback: CallbackQuery,
    callback_data: MyListCB,
    state,
    session: AsyncSession,
    user: object,
    i18n: I18n,
) -> None:
    listing = await listing_repo.get_simple(session, callback_data.id)
    if not listing or listing.user_id != user.id:
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return
    action = callback_data.action
    messages = {
        "hide": "my_listings.hidden",
        "unhide": "my_listings.unhidden",
        "renew": "my_listings.renewed",
        "sold": "my_listings.marked_sold",
        "rented": "my_listings.marked_rented",
        "archive": "my_listings.archived",
    }
    if action in {"hide", "unhide", "sold", "rented", "archive"}:
        target = {
            "hide": ListingStatus.HIDDEN,
            "unhide": ListingStatus.ACTIVE,
            "sold": ListingStatus.SOLD,
            "rented": ListingStatus.RENTED,
            "archive": ListingStatus.ARCHIVED,
        }[action]
        await change_status(session, callback.bot, listing, target, i18n)
        await answer(callback, i18n.t(messages[action]), reply_markup=my_listing_manage_kb(i18n, listing.id, target.value))
    elif action == "renew":
        listing.status = ListingStatus.PENDING
        listing.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.listing_ttl_days)
        listing.expiry_notified_at = None
        await answer(callback, i18n.t("my_listings.renewed"), reply_markup=my_listing_manage_kb(i18n, listing.id, "PENDING"))
    elif action == "delete":
        await answer(callback, i18n.t("my_listings.confirm_delete"), reply_markup=confirm_delete_kb(i18n, "delisting", listing.id))
    elif action == "change_price":
        await state.update_data(edit_price_listing_id=listing.id)
        await state.set_state(EditListing.price)
        await answer(callback, i18n.t("listing.ask_price"), reply_markup=skip_kb(i18n))
    elif action == "view":
        await answer(callback, format_full_listing(await listing_repo.get(session, listing.id), i18n), parse_mode="HTML")
    elif action == "refresh":
        listing.status = ListingStatus.PENDING
        await answer(callback, i18n.t("my_listings.renewed"), reply_markup=my_listing_manage_kb(i18n, listing.id, "PENDING"))
    await callback.answer()


@router.callback_query(ConfirmCB.filter(F.action.startswith("delisting_yes_")))
async def confirm_delete_listing(
    callback: CallbackQuery, session: AsyncSession, user: object, i18n: I18n
) -> None:
    listing_id = int(callback.data.rsplit("_", 1)[1])
    listing = await listing_repo.get_simple(session, listing_id)
    if not listing or listing.user_id != user.id:
        await callback.answer(i18n.t("common.access_denied"), show_alert=True)
        return
    await session.delete(listing)
    await answer(callback, i18n.t("my_listings.deleted"), reply_markup=main_menu_kb(i18n))
    await callback.answer()


@router.callback_query(ConfirmCB.filter(F.action.startswith("delisting_no_")))
async def cancel_delete_listing(callback: CallbackQuery, i18n: I18n) -> None:
    await answer(callback, i18n.t("common.cancel"), reply_markup=my_listings_kb(i18n))
    await callback.answer()


@router.message(EditListing.price)
async def change_price(message: Message, state, session: AsyncSession, user: object, i18n: I18n) -> None:
    data = await state.get_data()
    listing = await listing_repo.get_simple(session, data["edit_price_listing_id"])
    price = parse_decimal(message.text)
    if not listing or listing.user_id != user.id or not price:
        await message.answer(i18n.t("listing.invalid_price"))
        return
    listing.price = price
    await state.clear()
    await message.answer(i18n.t("listing.price_updated"), reply_markup=main_menu_kb(i18n))
