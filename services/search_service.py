from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Listing, ListingStatus
from database.repositories.listings import _load_listing
from database.repositories.interactions import add_search_log
from utils.pagination import SEARCH_PAGE_SIZE, paginate

SORT_MAP = {
    "new": lambda q: q.order_by(Listing.id.desc()),
    "cheap": lambda q: q.order_by(Listing.price.asc()),
    "expensive": lambda q: q.order_by(Listing.price.desc()),
    "area": lambda q: q.order_by(Listing.area.desc()),
}


def normalize_filters(raw: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw or {})
    for key in (
        "region_id",
        "district_id",
        "neighborhood_id",
        "property_type_id",
        "min_price",
        "max_price",
        "min_area",
        "max_area",
        "floor",
        "guests",
        "price_per_day",
    ):
        value = result.get(key)
        if value in (None, "", 0, "0"):
            result.pop(key, None)
            continue
        try:
            result[key] = int(value)
        except (ValueError, TypeError):
            result.pop(key, None)
    rooms = result.get("rooms")
    if isinstance(rooms, str):
        result["rooms"] = [int(x) for x in rooms.replace(" ", "").split(",") if x.isdigit()]
    if isinstance(rooms, int):
        result["rooms"] = [rooms]
    if not result.get("sort"):
        result["sort"] = "new"
    return result


def serialize_filters(filters: dict[str, Any]) -> dict[str, Any]:
    clean = {}
    for key, value in normalize_filters(filters).items():
        if isinstance(value, Decimal):
            clean[key] = str(value)
        elif isinstance(value, (str, int, float, bool, list, dict)) or value is None:
            clean[key] = value
    return clean


async def search(
    session: AsyncSession,
    filters: dict[str, Any],
    user_id: int | None = None,
    log: bool = True,
) -> list[Listing]:
    filters = normalize_filters(filters)
    query = _load_listing(select(Listing)).where(Listing.status == ListingStatus.ACTIVE)

    if filters.get("listing_type"):
        query = query.where(Listing.listing_type == filters["listing_type"])
    if filters.get("property_type_id"):
        query = query.where(Listing.property_type_id == filters["property_type_id"])
    if filters.get("region_id"):
        query = query.where(Listing.region_id == filters["region_id"])
    if filters.get("district_id"):
        query = query.where(Listing.district_id == filters["district_id"])
    if filters.get("neighborhood_id"):
        query = query.where(Listing.neighborhood_id == filters["neighborhood_id"])
    if filters.get("min_price"):
        query = query.where(Listing.price >= filters["min_price"])
    if filters.get("max_price"):
        query = query.where(Listing.price <= filters["max_price"])
    if filters.get("rooms"):
        query = query.where(Listing.rooms.in_(filters["rooms"]))
    if filters.get("min_area"):
        query = query.where(Listing.area >= filters["min_area"])
    if filters.get("max_area"):
        query = query.where(Listing.area <= filters["max_area"])
    if filters.get("floor"):
        query = query.where(Listing.floor == filters["floor"])
    if filters.get("condition"):
        query = query.where(Listing.condition == filters["condition"])
    if filters.get("renovation"):
        query = query.where(Listing.renovation == filters["renovation"])
    if filters.get("furnished") is not None:
        query = query.where(Listing.furnished == bool(filters["furnished"]))
    if filters.get("is_family_allowed") is not None:
        query = query.where(Listing.is_family_allowed.is_(bool(filters["is_family_allowed"])))
    if filters.get("is_student_allowed") is not None:
        query = query.where(Listing.is_student_allowed.is_(bool(filters["is_student_allowed"])))
    if filters.get("is_long_term") is not None:
        query = query.where(Listing.is_long_term.is_(bool(filters["is_long_term"])))
    if filters.get("has_deposit") is not None:
        query = query.where(Listing.has_deposit.is_(bool(filters["has_deposit"])))
    if filters.get("utilities_terms"):
        query = query.where(Listing.utilities_terms == filters["utilities_terms"])
    if filters.get("guests"):
        query = query.where(Listing.guests >= filters["guests"])
    if filters.get("query"):
        query = query.where(Listing.title.ilike(f"%{filters['query'].strip()}%"))

    sorter = SORT_MAP.get(filters.get("sort"), SORT_MAP["new"])
    query = sorter(query)

    if log:
        await add_search_log(
            session,
            user_id,
            property_type_id=filters.get("property_type_id"),
            region_id=filters.get("region_id"),
            query=filters.get("query"),
        )
    result = await session.execute(query)
    return list(result.scalars().all())


async def search_page(
    session: AsyncSession, filters: dict[str, Any], page: int, user_id: int | None = None
) -> tuple[list[Listing], int]:
    items = await search(session, filters, user_id=user_id)
    return paginate(items, page, SEARCH_PAGE_SIZE), len(items)


async def matches_saved_search(
    session: AsyncSession, saved: Any, listing: Listing
) -> bool:
    filters = normalize_filters(saved.filters or {})
    results = await search(session, filters, log=False)
    return any(item.id == listing.id for item in results)
