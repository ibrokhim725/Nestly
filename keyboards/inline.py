from __future__ import annotations

from typing import Any

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from utils.pagination import DEFAULT_PAGE_SIZE, SEARCH_PAGE_SIZE, total_pages


class NavCB(CallbackData, prefix="nav"):
    action: str


class DealCB(CallbackData, prefix="deal"):
    value: str


class PropCB(CallbackData, prefix="pt"):
    id: int
    code: str = ""


class RegionCB(CallbackData, prefix="rg"):
    id: int


class DistrictCB(CallbackData, prefix="ds"):
    id: int


class NbhdCB(CallbackData, prefix="nb"):
    id: int


class FilterCB(CallbackData, prefix="fl"):
    action: str
    value: str = ""


class CardCB(CallbackData, prefix="crd"):
    action: str
    id: int
    page: int = 1


class MyListCB(CallbackData, prefix="my"):
    action: str
    id: int = 0


class FavCB(CallbackData, prefix="fv"):
    action: str
    id: int
    page: int = 1


class PubCB(CallbackData, prefix="pub"):
    action: str
    id: int


class InqCB(CallbackData, prefix="inq"):
    action: str
    id: int


class ContactCB(CallbackData, prefix="ctc"):
    action: str
    id: int


class ViewCB(CallbackData, prefix="vw"):
    action: str
    id: int


class SavedCB(CallbackData, prefix="sv"):
    action: str
    id: int


class ReportCB(CallbackData, prefix="rpt"):
    action: str
    id: int


class AdminCB(CallbackData, prefix="adm"):
    action: str
    value: str = ""


class ProfileCB(CallbackData, prefix="prf"):
    action: str


class LegalCB(CallbackData, prefix="law"):
    doc: str


class PageCB(CallbackData, prefix="pg"):
    scope: str
    page: int
    id: int = 0


class ImgCB(CallbackData, prefix="img"):
    action: str
    id: int


class ConfirmCB(CallbackData, prefix="cfm"):
    action: str


def inline(*rows: list[InlineKeyboardButton]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.row(*row)
    return builder.as_markup()


def button(text: str, data: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data.pack())


def back_button(i18n: Any, action: str = "main") -> InlineKeyboardButton:
    return button(i18n.t("common.back"), NavCB(action=action))


# ---------- Reply keyboards ----------

def language_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🇺🇿 O‘zbek tili"),
        KeyboardButton(text="🇷🇺 Русский язык"),
    )
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def contact_kb(i18n: Any) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=i18n.t("registration.phone_button"), request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def location_kb(i18n: Any) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=i18n.t("common.send_location"), request_location=True))
    builder.row(KeyboardButton(text=i18n.t("common.skip")))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def skip_kb(i18n: Any) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=i18n.t("common.skip")))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def yes_no_kb(i18n: Any) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=i18n.t("common.yes")), KeyboardButton(text=i18n.t("common.no")))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def main_menu_kb(i18n: Any, is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=i18n.t("menu.search")),
        KeyboardButton(text=i18n.t("menu.post")),
    )
    builder.row(
        KeyboardButton(text=i18n.t("menu.favorites")),
        KeyboardButton(text=i18n.t("menu.my_listings")),
    )
    builder.row(
        KeyboardButton(text=i18n.t("menu.notifications")),
        KeyboardButton(text=i18n.t("menu.appointments")),
    )
    builder.row(
        KeyboardButton(text=i18n.t("menu.my_profile")),
        KeyboardButton(text=i18n.t("menu.help")),
    )
    if is_admin:
        builder.row(KeyboardButton(text=i18n.t("menu.admin")))
    return builder.as_markup(resize_keyboard=True)


def cancel_kb(i18n: Any) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=i18n.t("common.cancel")))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ---------- Search keyboards ----------

def search_deal_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [
            button(i18n.t("search.buy"), DealCB(value="SALE")),
            button(i18n.t("search.rent"), DealCB(value="RENT")),
        ],
        [
            button(i18n.t("search.daily"), DealCB(value="DAILY")),
            button(i18n.t("search.commercial"), DealCB(value="COMMERCIAL")),
        ],
        [
            button(i18n.t("search.quick_new"), FilterCB(action="quick", value="new")),
        ],
        [
            button(i18n.t("search.quick_cheap"), FilterCB(action="quick", value="cheap")),
            button(i18n.t("search.quick_expensive"), FilterCB(action="quick", value="expensive")),
        ],
        [button(i18n.t("search.by_title"), FilterCB(action="by_title"))],
        [button(i18n.t("common.back"), NavCB(action="main"))],
    )


def commercial_deal_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [
            button(i18n.t("inquiry.purpose_buy"), DealCB(value="COMMERCIAL_SALE")),
            button(i18n.t("inquiry.purpose_rent"), DealCB(value="COMMERCIAL_RENT")),
        ],
        [button(i18n.t("common.back"), NavCB(action="search"))],
    )


def property_type_kb(i18n: Any, types: list[Any], scope: str = "search") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ptype in types:
        name = getattr(ptype, f"name_{i18n.lang}", None) or ptype.name_uz
        builder.button(text=name, callback_data=PropCB(id=ptype.id, code=ptype.code))
    builder.adjust(2)
    builder.row(button(i18n.t("common.back"), NavCB(action=scope)))
    return builder.as_markup()


def regions_kb(i18n: Any, regions: list[Any], scope: str = "search") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for region in regions:
        name = getattr(region, f"name_{i18n.lang}", None) or region.name_uz
        builder.button(text=name, callback_data=RegionCB(id=region.id))
    builder.adjust(2)
    builder.row(button(i18n.t("common.back"), NavCB(action=scope)))
    return builder.as_markup()


def districts_kb(i18n: Any, districts: list[Any], scope: str = "search") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for district in districts:
        name = getattr(district, f"name_{i18n.lang}", None) or district.name_uz
        builder.button(text=name, callback_data=DistrictCB(id=district.id))
    builder.adjust(2)
    if scope == "search":
        builder.row(button(i18n.t("search.all_districts"), FilterCB(action="skip_district")))
    builder.row(button(i18n.t("common.back"), NavCB(action="regions")))
    return builder.as_markup()


def neighborhoods_kb(i18n: Any, items: list[Any]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        name = getattr(item, f"name_{i18n.lang}", None) or item.name_uz
        builder.button(text=name, callback_data=NbhdCB(id=item.id))
    builder.adjust(2)
    builder.row(button(i18n.t("common.skip"), FilterCB(action="skip_nbhd")))
    return builder.as_markup()


FILTER_ACTIONS = [
    ("rooms", "🛏"),
    ("floor", "🏢"),
    ("condition", "🏚"),
    ("renovation", "🔧"),
    ("furnished", "🪑"),
    ("family", "👨‍👩‍👧"),
    ("students", "🎓"),
    ("long_term", "📆"),
    ("deposit", "💵"),
    ("utilities", "🧾"),
    ("guests", "👥"),
]


def filter_menu_kb(i18n: Any, selected: dict[str, Any] | None = None) -> InlineKeyboardMarkup:
    selected = selected or {}
    builder = InlineKeyboardBuilder()
    for action, icon in FILTER_ACTIONS:
        mark = "✅" if selected.get(action) not in (None, "", False) else ""
        builder.button(text=f"{mark}{icon}", callback_data=FilterCB(action=action))
    builder.adjust(5)
    builder.row(button(i18n.t("search.show_results"), FilterCB(action="show")))
    builder.row(
        button(i18n.t("search.sort_new"), FilterCB(action="sort", value="new")),
        button(i18n.t("search.sort_cheap"), FilterCB(action="sort", value="cheap")),
    )
    builder.row(
        button(i18n.t("search.sort_expensive"), FilterCB(action="sort", value="expensive")),
        button(i18n.t("search.sort_area"), FilterCB(action="sort", value="area")),
    )
    builder.row(button(i18n.t("search.save_search"), FilterCB(action="save")))
    builder.row(button(i18n.t("common.back"), NavCB(action="search")))
    return builder.as_markup()


def choices_kb(
    i18n: Any, options: list[tuple[str, str]], action: str, with_skip: bool = True
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, value in options:
        builder.button(text=label, callback_data=FilterCB(action=action, value=value))
    builder.adjust(2)
    if with_skip:
        builder.row(button(i18n.t("common.skip"), FilterCB(action="skip", value=action)))
    return builder.as_markup()


def condition_kb(i18n: Any) -> InlineKeyboardMarkup:
    return choices_kb(
        i18n,
        [
            (i18n.t("condition.new"), "new"),
            (i18n.t("condition.good"), "good"),
            (i18n.t("condition.old"), "old"),
        ],
        "condition",
    )


def renovation_kb(i18n: Any) -> InlineKeyboardMarkup:
    return choices_kb(
        i18n,
        [
            (i18n.t("renovation.renovated"), "renovated"),
            (i18n.t("renovation.needs"), "needs"),
            (i18n.t("renovation.none"), "none"),
        ],
        "renovation",
    )


def furnished_kb(i18n: Any, action: str = "furnished") -> InlineKeyboardMarkup:
    return choices_kb(
        i18n,
        [(i18n.t("furnished.yes"), "1"), (i18n.t("furnished.no"), "0")],
        action,
    )


def bool_kb(i18n: Any, action: str) -> InlineKeyboardMarkup:
    return choices_kb(i18n, [(i18n.t("common.yes"), "1"), (i18n.t("common.no"), "0")], action)


def utilities_kb(i18n: Any, action: str = "utilities") -> InlineKeyboardMarkup:
    return choices_kb(
        i18n,
        [
            (i18n.t("utilities.included"), "included"),
            (i18n.t("utilities.separate"), "separate"),
            (i18n.t("utilities.partial"), "partial"),
        ],
        action,
    )


def amenities_kb(i18n: Any, selected: list[str] | None = None) -> InlineKeyboardMarkup:
    selected = selected or []
    builder = InlineKeyboardBuilder()
    for key in ("wifi", "parking", "aircon", "kitchen", "tv", "balcony", "pool", "pets"):
        mark = "✅" if key in selected else ""
        builder.button(
            text=f"{mark}{i18n.t('amenities.' + key)}",
            callback_data=FilterCB(action="amenity", value=key),
        )
    builder.adjust(2)
    builder.row(button(i18n.t("common.done"), FilterCB(action="amenities_done")))
    return builder.as_markup()


# ---------- Listing cards ----------

def pagination_row(
    i18n: Any,
    scope: str,
    page: int,
    total: int,
    id: int = 0,
    per_page: int = DEFAULT_PAGE_SIZE,
) -> list[InlineKeyboardButton]:
    pages = total_pages(total, per_page)
    row = []
    if page > 1:
        row.append(button(i18n.t("common.prev"), PageCB(scope=scope, page=page - 1, id=id)))
    row.append(InlineKeyboardButton(text=f"{page}/{pages}", callback_data="noop"))
    if page < pages:
        row.append(button(i18n.t("common.next"), PageCB(scope=scope, page=page + 1, id=id)))
    return row


def listing_card_kb(i18n: Any, listing_id: int, page: int, is_favorite: bool) -> InlineKeyboardMarkup:
    fav_key = "listing_card.remove_favorite" if is_favorite else "listing_card.add_favorite"
    fav_action = "unfav" if is_favorite else "fav"
    return inline(
        [button(i18n.t(fav_key), FavCB(action=fav_action, id=listing_id, page=page))],
        [
            button(i18n.t("listing_card.contact_owner"), CardCB(action="contact", id=listing_id, page=page)),
        ],
        [
            button(i18n.t("listing_card.schedule_viewing"), CardCB(action="viewing", id=listing_id, page=page)),
        ],
        [
            button(i18n.t("listing_card.share"), CardCB(action="share", id=listing_id, page=page)),
            button(i18n.t("listing_card.report"), CardCB(action="report", id=listing_id, page=page)),
        ],
        [
            button(i18n.t("search.change_filters"), NavCB(action="search_filters")),
            button(i18n.t("common.main_menu"), NavCB(action="main")),
        ],
    )


def gallery_kb(i18n: Any, listing_id: int, page: int, photos: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, _ in enumerate(photos):
        builder.button(text=str(index + 1), callback_data=CardCB(action="photo", id=listing_id, page=index))
    builder.adjust(5)
    builder.row(button(i18n.t("common.back"), CardCB(action="back", id=listing_id, page=page)))
    return builder.as_markup()


def results_nav_kb(i18n: Any, page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*pagination_row(i18n, "results", page, total, per_page=SEARCH_PAGE_SIZE))
    builder.row(button(i18n.t("search.change_filters"), NavCB(action="search_filters")))
    builder.row(button(i18n.t("common.main_menu"), NavCB(action="main")))
    return builder.as_markup()


# ---------- Listing creation ----------

def post_type_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("listing.sale"), DealCB(value="SALE"))],
        [button(i18n.t("listing.rent"), DealCB(value="RENT"))],
        [button(i18n.t("listing.daily"), DealCB(value="DAILY"))],
        [button(i18n.t("listing.commercial_sale"), DealCB(value="COMMERCIAL_SALE"))],
        [button(i18n.t("listing.commercial_rent"), DealCB(value="COMMERCIAL_RENT"))],
        [button(i18n.t("listing.land_sale"), DealCB(value="LAND_SALE"))],
        [button(i18n.t("common.cancel"), NavCB(action="cancel"))],
    )


def price_unit_kb(i18n: Any) -> InlineKeyboardMarkup:
    return choices_kb(
        i18n,
        [
            (i18n.t("price_unit.total"), "TOTAL"),
            (i18n.t("price_unit.month"), "MONTH"),
            (i18n.t("price_unit.day"), "DAY"),
        ],
        "price_unit",
        with_skip=False,
    )


def preview_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("listing.confirm_send"), ConfirmCB(action="send"))],
        [button(i18n.t("listing.edit"), ConfirmCB(action="edit"))],
        [button(i18n.t("common.cancel"), ConfirmCB(action="cancel"))],
    )


def edit_fields_kb(i18n: Any) -> InlineKeyboardMarkup:
    fields = [
        ("title", "🏷"),
        ("description", "📝"),
        ("price", "💰"),
        ("area", "📐"),
        ("rooms", "🛏"),
        ("contact_phone", "📞"),
    ]
    builder = InlineKeyboardBuilder()
    for key, icon in fields:
        builder.button(text=f"{icon}{key}", callback_data=FilterCB(action="edit_field", value=key))
    builder.adjust(2)
    builder.row(button(i18n.t("common.done"), ConfirmCB(action="back_preview")))
    return builder.as_markup()


def images_kb(i18n: Any, count: int, min_images: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if count > 0:
        builder.button(text="⭐", callback_data=ImgCB(action="primary_menu", id=0))
        builder.button(text="🗑", callback_data=ImgCB(action="delete_menu", id=0))
        builder.button(text="↔️", callback_data=ImgCB(action="move_menu", id=0))
    builder.adjust(3)
    builder.row(button(i18n.t("common.done"), ConfirmCB(action="images_done")))
    builder.row(button(i18n.t("common.cancel"), NavCB(action="cancel")))
    return builder.as_markup()


def image_index_kb(i18n: Any, images: list[Any], action: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, image in enumerate(images):
        builder.button(text=str(index + 1), callback_data=ImgCB(action=action, id=image.id))
    builder.adjust(5)
    builder.row(button(i18n.t("common.back"), ImgCB(action="images_back", id=0)))
    return builder.as_markup()


def video_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("common.yes"), ConfirmCB(action="video_yes"))],
        [button(i18n.t("common.no"), ConfirmCB(action="video_no"))],
    )


# ---------- My listings ----------

def my_listings_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("my_listings.active"), MyListCB(action="active"))],
        [button(i18n.t("my_listings.pending"), MyListCB(action="pending"))],
        [button(i18n.t("my_listings.rejected"), MyListCB(action="rejected"))],
        [button(i18n.t("my_listings.sold"), MyListCB(action="sold")),
         button(i18n.t("my_listings.rented"), MyListCB(action="rented"))],
        [button(i18n.t("my_listings.archived"), MyListCB(action="archived"))],
        [button(i18n.t("common.main_menu"), NavCB(action="main"))],
    )


def my_listing_manage_kb(i18n: Any, listing_id: int, status: str) -> InlineKeyboardMarkup:
    rows = [
        [button(i18n.t("my_listings.view"), MyListCB(action="view", id=listing_id)),
         button(i18n.t("my_listings.edit"), MyListCB(action="refresh", id=listing_id))],
        [button(i18n.t("my_listings.change_price"), MyListCB(action="change_price", id=listing_id))],
    ]
    if status == "HIDDEN":
        rows.append([button(i18n.t("my_listings.unhide"), MyListCB(action="unhide", id=listing_id))])
    else:
        rows.append([button(i18n.t("my_listings.hide"), MyListCB(action="hide", id=listing_id))])
    rows.append([button(i18n.t("my_listings.renew"), MyListCB(action="renew", id=listing_id))])
    rows.append([
        button(i18n.t("my_listings.mark_sold"), MyListCB(action="sold", id=listing_id)),
        button(i18n.t("my_listings.mark_rented"), MyListCB(action="rented", id=listing_id)),
    ])
    rows.append([
        button(i18n.t("my_listings.archive"), MyListCB(action="archive", id=listing_id)),
        button(i18n.t("my_listings.delete"), MyListCB(action="delete", id=listing_id)),
    ])
    rows.append([button(i18n.t("common.back"), MyListCB(action="back"))])
    return inline(*rows)


def confirm_delete_kb(i18n: Any, action: str, id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("common.yes"), ConfirmCB(action=f"{action}_yes_{id}"))],
        [button(i18n.t("common.no"), ConfirmCB(action=f"{action}_no_{id}"))],
    )


# ---------- Interactions ----------

def inquiry_actions_kb(i18n: Any, inquiry_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("inquiry.reply"), InqCB(action="reply", id=inquiry_id))],
        [button(i18n.t("inquiry.share_contact"), InqCB(action="contact", id=inquiry_id))],
        [button(i18n.t("inquiry.decline"), InqCB(action="decline", id=inquiry_id))],
    )


def contact_actions_kb(i18n: Any, request_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("inquiry.share_contact"), ContactCB(action="accept", id=request_id))],
        [button(i18n.t("inquiry.decline"), ContactCB(action="decline", id=request_id))],
    )


def viewing_actions_kb(i18n: Any, viewing_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("viewing.confirm"), ViewCB(action="confirm", id=viewing_id))],
        [button(i18n.t("viewing.reschedule"), ViewCB(action="reschedule", id=viewing_id))],
        [button(i18n.t("viewing.decline"), ViewCB(action="decline", id=viewing_id)),
         button(i18n.t("viewing.cancel"), ViewCB(action="cancel", id=viewing_id))],
    )


def report_reasons_kb(i18n: Any, listing_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for reason in ("fake", "wrong_price", "other_photo", "wrong_info", "suspicious_user", "other"):
        builder.button(
            text=i18n.t("report." + reason),
            callback_data=FilterCB(action="report_reason", value=reason),
        )
    builder.adjust(2)
    return builder.as_markup()


def saved_search_kb(i18n: Any, search_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("saved_search.toggle"), SavedCB(action="toggle", id=search_id))],
        [button(i18n.t("saved_search.delete"), SavedCB(action="delete", id=search_id))],
    )


def notifications_kb(i18n: Any, unread: int) -> InlineKeyboardMarkup:
    rows = []
    if unread:
        rows.append([button(i18n.t("notifications.mark_all_read"), ProfileCB(action="read_notifications"))])
    rows.append([button(i18n.t("common.main_menu"), NavCB(action="main"))])
    return inline(*rows)


# ---------- Profile & legal ----------

def profile_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("profile.edit"), ProfileCB(action="edit"))],
        [button(i18n.t("profile.notifications"), ProfileCB(action="notifications"))],
        [button(i18n.t("menu.saved_searches"), ProfileCB(action="saved_searches"))],
        [button(i18n.t("profile.legal"), ProfileCB(action="legal"))],
        [button(i18n.t("profile.delete_request"), ProfileCB(action="delete_request"))],
        [button(i18n.t("common.main_menu"), NavCB(action="main"))],
    )


def edit_profile_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button("✏️ " + i18n.t("profile.edit_name"), ProfileCB(action="edit_first_name")),
         button("✏️ " + i18n.t("profile.edit_last_name"), ProfileCB(action="edit_last_name"))],
        [button("📞", ProfileCB(action="edit_phone")),
         button("👤", ProfileCB(action="edit_profile_type"))],
        [button("🌐", ProfileCB(action="edit_language"))],
        [button(i18n.t("common.back"), ProfileCB(action="back"))],
    )


def profile_type_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("profile_type.owner"), FilterCB(action="profile_type", value="OWNER"))],
        [button(i18n.t("profile_type.agent"), FilterCB(action="profile_type", value="AGENT"))],
        [button(i18n.t("profile_type.developer"), FilterCB(action="profile_type", value="DEVELOPER"))],
    )


def legal_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button("📄 " + ("Foydalanish shartlari" if i18n.lang == "uz" else "Условия"), LegalCB(doc="terms"))],
        [button("🔒 " + ("Maxfiylik siyosati" if i18n.lang == "uz" else "Конфиденциальность"), LegalCB(doc="privacy"))],
        [button("📋 " + ("E'lon qoidalari" if i18n.lang == "uz" else "Правила"), LegalCB(doc="rules"))],
        [button("🛡 " + ("Xavfsizlik" if i18n.lang == "uz" else "Безопасность"), LegalCB(doc="safety"))],
        [button("☎️ " + ("Aloqa" if i18n.lang == "uz" else "Контакты"), LegalCB(doc="contact_info"))],
        [button(i18n.t("common.main_menu"), NavCB(action="main"))],
    )


def help_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("help.contact_admin"), AdminCB(action="contact_admin"))],
        [button(i18n.t("profile.legal"), NavCB(action="legal"))],
        [button(i18n.t("common.main_menu"), NavCB(action="main"))],
    )


def terms_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("common.yes"), ConfirmCB(action="terms_yes"))],
        [button(i18n.t("common.no"), ConfirmCB(action="terms_no"))],
        [button(i18n.t("profile.legal"), NavCB(action="legal"))],
    )


# ---------- Admin ----------

def admin_menu_kb(i18n: Any) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action, label in (
        ("stats", "stats"),
        ("all_listings", "all_listings"),
        ("pending", "pending"),
        ("users", "users"),
        ("inquiries", "inquiries"),
        ("viewings", "viewings"),
        ("reports", "reports"),
        ("regions", "regions"),
        ("settings", "settings"),
        ("broadcast", "broadcast"),
        ("activity", "activity"),
    ):
        builder.button(text=i18n.t("admin." + label), callback_data=AdminCB(action=action))
    builder.adjust(2)
    return builder.as_markup()


def stats_period_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("admin.day"), AdminCB(action="stats_day")),
         button(i18n.t("admin.week"), AdminCB(action="stats_week")),
         button(i18n.t("admin.month"), AdminCB(action="stats_month"))],
        [button(i18n.t("admin.back"), AdminCB(action="menu"))],
    )


def moderation_kb(i18n: Any, listing_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("admin.approve"), PubCB(action="approve", id=listing_id))],
        [button(i18n.t("admin.reject"), PubCB(action="reject", id=listing_id)),
         button(i18n.t("admin.require_fix"), PubCB(action="fix", id=listing_id))],
        [button(i18n.t("admin.suspicious"), PubCB(action="suspicious", id=listing_id))],
        [button(i18n.t("admin.back"), AdminCB(action="pending"))],
    )


def user_manage_kb(i18n: Any, user_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("admin.warn"), AdminCB(action="warn", value=str(user_id)))],
        [button(i18n.t("admin.block_temp"), AdminCB(action="block_temp", value=str(user_id))),
         button(i18n.t("admin.block_perm"), AdminCB(action="block_perm", value=str(user_id)))],
        [button(i18n.t("admin.unblock"), AdminCB(action="unblock", value=str(user_id)))],
        [button(i18n.t("admin.back"), AdminCB(action="users"))],
    )


def report_actions_kb(i18n: Any, report_id: int) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("admin.resolve"), ReportCB(action="resolve", id=report_id)),
         button(i18n.t("admin.dismiss"), ReportCB(action="dismiss", id=report_id))],
        [button(i18n.t("admin.back"), AdminCB(action="reports"))],
    )


def broadcast_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("admin.seg_all"), AdminCB(action="seg", value="all"))],
        [button(i18n.t("admin.seg_searchers"), AdminCB(action="seg", value="searchers"))],
        [button(i18n.t("admin.seg_posters"), AdminCB(action="seg", value="posters"))],
        [button(i18n.t("admin.seg_region"), AdminCB(action="seg", value="region"))],
        [button(i18n.t("admin.back"), AdminCB(action="menu"))],
    )


def regions_admin_kb(i18n: Any) -> InlineKeyboardMarkup:
    return inline(
        [button(i18n.t("admin.add_region"), AdminCB(action="add_region"))],
        [button(i18n.t("admin.add_district"), AdminCB(action="add_district"))],
        [button(i18n.t("admin.back"), AdminCB(action="menu"))],
    )


def admin_pagination_kb(i18n: Any, scope: str, page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*pagination_row(i18n, scope, page, total))
    builder.row(button(i18n.t("admin.back"), AdminCB(action="menu")))
    return builder.as_markup()
