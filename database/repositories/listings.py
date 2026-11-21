from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Listing,
    ListingImage,
    ListingStatus,
    ListingVideo,
    User,
)


def _load_listing(query):
    return query.options(
        selectinload(Listing.owner).selectinload(User.profile),
        selectinload(Listing.region),
        selectinload(Listing.district),
        selectinload(Listing.neighborhood),
        selectinload(Listing.property_type),
        selectinload(Listing.images),
        selectinload(Listing.videos),
    )


async def get(session: AsyncSession, listing_id: int) -> Listing | None:
    result = await session.execute(_load_listing(select(Listing)).where(Listing.id == listing_id))
    return result.scalar_one_or_none()


async def get_simple(session: AsyncSession, listing_id: int) -> Listing | None:
    return await session.get(Listing, listing_id)


async def create(session: AsyncSession, **kwargs: Any) -> Listing:
    listing = Listing(**kwargs)
    session.add(listing)
    await session.flush()
    return listing


async def list_by_user(
    session: AsyncSession,
    user_id: int,
    statuses: list[ListingStatus] | None = None,
) -> list[Listing]:
    query = _load_listing(select(Listing)).where(Listing.user_id == user_id)
    if statuses:
        query = query.where(Listing.status.in_(statuses))
    result = await session.execute(query.order_by(Listing.id.desc()))
    return list(result.scalars().all())


async def list_by_status(
    session: AsyncSession, statuses: list[ListingStatus]
) -> list[Listing]:
    result = await session.execute(
        _load_listing(select(Listing))
        .where(Listing.status.in_(statuses))
        .order_by(Listing.id.desc())
    )
    return list(result.scalars().all())


async def list_all(session: AsyncSession, limit: int = 50, offset: int = 0) -> list[Listing]:
    result = await session.execute(
        _load_listing(select(Listing)).order_by(Listing.id.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def count_by_status(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(
        select(Listing.status, func.count(Listing.id)).group_by(Listing.status)
    )
    return {str(status.value): int(count) for status, count in result.all()}


async def count_by_user_and_status(
    session: AsyncSession, user_id: int, status: ListingStatus
) -> int:
    return int(
        await session.scalar(
            select(func.count(Listing.id)).where(
                Listing.user_id == user_id, Listing.status == status
            )
        )
        or 0
    )


async def count_by_user(session: AsyncSession, user_id: int) -> int:
    return int(
        await session.scalar(select(func.count(Listing.id)).where(Listing.user_id == user_id))
        or 0
    )


async def find_duplicate(
    session: AsyncSession,
    user_id: int,
    title: str,
    price: Decimal | int,
    region_id: int,
) -> Listing | None:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await session.execute(
        select(Listing).where(
            Listing.user_id == user_id,
            Listing.title == title.strip(),
            Listing.price == Decimal(str(price)),
            Listing.region_id == region_id,
            Listing.created_at >= since,
            Listing.status.notin_([ListingStatus.ARCHIVED, ListingStatus.REJECTED]),
        )
    )
    return result.scalars().first()


async def add_image(session: AsyncSession, listing_id: int, file_id: str, position: int) -> ListingImage:
    image = ListingImage(listing_id=listing_id, file_id=file_id, position=position, is_primary=position == 0)
    session.add(image)
    await session.flush()
    return image


async def delete_image(session: AsyncSession, image_id: int) -> None:
    image = await session.get(ListingImage, image_id)
    if image:
        await session.delete(image)
        await session.flush()


async def set_primary_image(session: AsyncSession, listing_id: int, image_id: int) -> None:
    images = (
        await session.execute(
            select(ListingImage).where(ListingImage.listing_id == listing_id)
        )
    ).scalars().all()
    for image in images:
        image.is_primary = image.id == image_id
    await session.flush()


async def move_image(session: AsyncSession, image_id: int, direction: int) -> None:
    image = await session.get(ListingImage, image_id)
    if not image:
        return
    siblings = (
        await session.execute(
            select(ListingImage)
            .where(ListingImage.listing_id == image.listing_id)
            .order_by(ListingImage.position)
        )
    ).scalars().all()
    index = next((i for i, item in enumerate(siblings) if item.id == image_id), -1)
    target = index + direction
    if index < 0 or target < 0 or target >= len(siblings):
        return
    siblings[index].position, siblings[target].position = (
        siblings[target].position,
        siblings[index].position,
    )
    await session.flush()


async def add_video(session: AsyncSession, listing_id: int, file_id: str) -> ListingVideo:
    video = ListingVideo(listing_id=listing_id, file_id=file_id)
    session.add(video)
    await session.flush()
    return video


async def increment_views(session: AsyncSession, listing_id: int) -> None:
    listing = await session.get(Listing, listing_id)
    if listing:
        listing.views_count += 1
        await session.flush()


async def get_expiring(session: AsyncSession, within_days: int) -> list[Listing]:
    deadline = datetime.now(timezone.utc) + timedelta(days=within_days)
    result = await session.execute(
        _load_listing(select(Listing)).where(
            Listing.status == ListingStatus.ACTIVE,
            Listing.expires_at.is_not(None),
            Listing.expires_at <= deadline,
            Listing.expiry_notified_at.is_(None),
        )
    )
    return list(result.scalars().all())


async def expire_old(session: AsyncSession) -> list[Listing]:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        _load_listing(select(Listing)).where(
            Listing.status == ListingStatus.ACTIVE,
            Listing.expires_at.is_not(None),
            Listing.expires_at <= now,
        )
    )
    return list(result.scalars().all())


async def top_regions(session: AsyncSession, limit: int = 5) -> list[tuple[str, int]]:
    result = await session.execute(
        select(Listing.region_id, func.count(Listing.id))
        .group_by(Listing.region_id)
        .order_by(func.count(Listing.id).desc())
        .limit(limit)
    )
    from database.models import Region

    rows = []
    for region_id, count in result.all():
        region = await session.get(Region, region_id)
        rows.append((region.name_uz if region else str(region_id), int(count)))
    return rows
