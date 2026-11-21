from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from html import escape
from typing import Any

from utils.i18n import I18n

PRICE_UNITS = {"total": "total", "month": "month", "day": "day"}


def format_price(value: Decimal | int | float | None, i18n: I18n | None = None) -> str:
    if value is None:
        return "—"
    number = int(Decimal(str(value)))
    formatted = f"{number:,}".replace(",", " ")
    suffix = " so'm" if i18n is None or i18n.lang == "uz" else " сум"
    return f"{formatted}{suffix}"


def format_date(value: datetime | date | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d.%m.%Y")


def price_label(unit: str | None, i18n: I18n) -> str:
    return i18n.t(f"price_unit.{unit or 'total'}")


def _localized_name(obj: Any, i18n: I18n) -> str:
    if obj is None:
        return "—"
    return getattr(obj, f"name_{i18n.lang}", None) or obj.name_uz or "—"


def format_listing_card(listing: Any, i18n: I18n) -> str:
    region = _localized_name(getattr(listing, "region", None), i18n)
    district = _localized_name(getattr(listing, "district", None), i18n)
    location = f"{region}, {district}" if district and district != "—" else region

    lines = [
        f"🏡 <b>{escape(listing.title or '')}</b>",
        "",
        f"📍 {escape(location)}",
        f"💰 {format_price(listing.price, i18n)} / {price_label(listing.price_unit, i18n)}",
    ]
    if listing.rooms is not None:
        lines.append(f"🛏 {i18n.t('listing_card.rooms')}: {listing.rooms}")
    if listing.area is not None:
        lines.append(f"📐 {i18n.t('listing_card.area')}: {listing.area} m²")
    if listing.floor is not None:
        floor_text = f"{listing.floor}"
        if listing.total_floors:
            floor_text += f" / {listing.total_floors}"
        lines.append(f"🏢 {i18n.t('listing_card.floor')}: {floor_text}")
    if listing.condition:
        lines.append(f"✅ {i18n.t(f'condition.{listing.condition}')}")
    if listing.furnished is not None:
        furnished_key = "furnished.yes" if listing.furnished else "furnished.no"
        lines.append(f"🪑 {i18n.t(furnished_key)}")
    lines.append("")
    lines.append(f"{i18n.t('listing_card.status')}: {i18n.t(f'listing_status.{listing.status}')}")
    lines.append(f"{i18n.t('listing_card.posted')}: {format_date(listing.created_at)}")
    return "\n".join(lines)


def format_full_listing(listing: Any, i18n: I18n, owner: Any | None = None) -> str:
    lines = [format_listing_card(listing, i18n), ""]
    if listing.description:
        lines += [f"📝 {escape(listing.description)}", ""]
    details = []
    if listing.built_year:
        details.append(f"🏗 {listing.built_year}")
    if listing.renovation:
        details.append(i18n.t(f"renovation.{listing.renovation}"))
    if listing.extra:
        details.append(escape(listing.extra))
    if details:
        lines += [" • ".join(details), ""]
    if owner:
        name = " ".join(filter(None, [owner.first_name, owner.last_name])) or "—"
        lines.append(i18n.t("listing_card.seller", name=escape(name)))
        badges = []
        if owner.is_phone_verified:
            badges.append("✅ " + i18n.t("listing_card.verified_phone"))
        if owner.is_profile_verified:
            badges.append("✅ " + i18n.t("listing_card.verified_profile"))
        if owner.is_documents_verified:
            badges.append("✅ " + i18n.t("listing_card.verified_docs"))
        if badges:
            lines.append("\n".join(badges))
    lines += ["", i18n.t("listing_card.location_notice")]
    return "\n".join(lines)


def summarize_filters(filters: dict[str, Any], i18n: I18n) -> str:
    parts = []
    if filters.get("region_name"):
        parts.append(filters["region_name"])
    if filters.get("district_name"):
        parts.append(filters["district_name"])
    if filters.get("rooms"):
        parts.append(f"{filters['rooms']} xona")
    if filters.get("min_price") or filters.get("max_price"):
        parts.append(
            f"{format_price(filters.get('min_price'), i18n)} – "
            f"{format_price(filters.get('max_price'), i18n)}"
        )
    return ", ".join(parts) or i18n.t("common.all")
