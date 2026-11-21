from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.models import Listing, ListingStatus, PriceUnit
from database.repositories import listings as listing_repo
from utils.formatters import format_price
from utils.i18n import I18n

PROPERTY_TITLES = {
    "apartment": {"uz": "kvartira", "ru": "квартира"},
    "house": {"uz": "hovli", "ru": "дом"},
    "new_building": {"uz": "yangi qurilgan uy", "ru": "новостройка"},
    "land": {"uz": "yer maydoni", "ru": "земельный участок"},
    "commercial": {"uz": "tijorat binosi", "ru": "коммерческое здание"},
    "dacha": {"uz": "dacha", "ru": "дача"},
    "office": {"uz": "ofis", "ru": "офис"},
    "shop": {"uz": "do'kon", "ru": "магазин"},
    "warehouse": {"uz": "ombor", "ru": "склад"},
    "production": {"uz": "ishlab chiqarish binosi", "ru": "производственное здание"},
    "restaurant": {"uz": "restoran uchun joy", "ru": "помещение под ресторан"},
    "non_residential_land": {"uz": "noturar yer maydoni", "ru": "нежилая земля"},
}


def build_title(data: dict[str, Any], i18n: I18n) -> str:
    code = data.get("property_type_code") or "apartment"
    name = PROPERTY_TITLES.get(code, {}).get(i18n.lang, code)
    rooms = data.get("rooms")
    if rooms and code not in {"land", "non_residential_land"}:
        return f"{rooms} xonali {name}" if i18n.lang == "uz" else f"{rooms}-комн. {name}"
    return name.capitalize()


def format_preview(data: dict[str, Any], i18n: I18n) -> str:
    lines = [
        f"🏡 <b>{build_title(data, i18n)}</b>",
        "",
        f"📍 {data.get('region_name', '—')} / {data.get('district_name', '—')}",
        f"💰 {format_price(Decimal(str(data.get('price', 0))), i18n)} / "
        f"{i18n.t('price_unit.' + str(data.get('price_unit', 'TOTAL')).lower())}",
        f"📐 {data.get('area')} m²",
    ]
    if data.get("description"):
        lines += ["", data["description"]]
    return "\n".join(lines)


async def submit_listing(
    session: AsyncSession,
    user_id: int,
    data: dict[str, Any],
    i18n: I18n,
    status: ListingStatus = ListingStatus.PENDING,
) -> Listing | None:
    price = Decimal(str(data["price"]))
    if status != ListingStatus.DRAFT:
        duplicate = await listing_repo.find_duplicate(
            session, user_id, build_title(data, i18n), price, data["region_id"]
        )
        if duplicate:
            return None

    now = datetime.now(timezone.utc)

    listing = await listing_repo.create(
        session,
        user_id=user_id,
        listing_type=data["listing_type"],
        property_type_id=data["property_type_id"],
        region_id=data["region_id"],
        district_id=data["district_id"],
        neighborhood_id=data.get("neighborhood_id"),
        title=build_title(data, i18n),
        description=data.get("description") or "",
        extra=data.get("extra"),
        price=price,
        price_unit=PriceUnit(str(data.get("price_unit", "TOTAL"))),
        area=Decimal(str(data["area"])),
        rooms=data.get("rooms"),
        floor=data.get("floor"),
        total_floors=data.get("total_floors"),
        built_year=data.get("built_year"),
        condition=data.get("condition"),
        renovation=data.get("renovation"),
        furnished=data.get("furnished"),
        is_family_allowed=data.get("is_family_allowed"),
        is_student_allowed=data.get("is_student_allowed"),
        is_long_term=data.get("is_long_term"),
        has_deposit=data.get("has_deposit"),
        utilities_terms=data.get("utilities_terms"),
        guests=data.get("guests"),
        amenities=data.get("amenities") or [],
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        contact_phone=data.get("contact_phone") or "",
        status=status,
        published_at=now if status != ListingStatus.DRAFT else None,
        expires_at=now + timedelta(days=settings.listing_ttl_days),
    )
    await session.flush()
    return listing
