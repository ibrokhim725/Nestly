from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Broadcast,
    ContactRequest,
    Favorite,
    Inquiry,
    Listing,
    ModerationLog,
    Notification,
    Report,
    ReportStatus,
    SavedSearch,
    SearchLog,
    User,
    ViewingRequest,
)


# ---------------- Favorites ----------------

async def is_favorite(session: AsyncSession, user_id: int, listing_id: int) -> bool:
    result = await session.execute(
        select(Favorite.id).where(
            Favorite.user_id == user_id, Favorite.listing_id == listing_id
        )
    )
    return result.scalar_one_or_none() is not None


async def add_favorite(session: AsyncSession, user_id: int, listing_id: int) -> bool:
    if await is_favorite(session, user_id, listing_id):
        return False
    session.add(Favorite(user_id=user_id, listing_id=listing_id))
    await session.flush()
    return True


async def remove_favorite(session: AsyncSession, user_id: int, listing_id: int) -> bool:
    result = await session.execute(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.listing_id == listing_id)
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        return False
    await session.delete(favorite)
    await session.flush()
    return True


async def list_favorites(session: AsyncSession, user_id: int) -> list[Listing]:
    from database.repositories.listings import _load_listing

    result = await session.execute(
        _load_listing(select(Listing))
        .join(Favorite, Favorite.listing_id == Listing.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.id.desc())
    )
    return list(result.scalars().all())


async def favorite_user_ids(session: AsyncSession, listing_id: int) -> list[int]:
    result = await session.execute(
        select(Favorite.user_id).where(Favorite.listing_id == listing_id)
    )
    return [int(value) for value in result.scalars().all()]


# ---------------- Saved searches ----------------

async def create_saved_search(
    session: AsyncSession, user_id: int, name: str, filters: dict[str, Any]
) -> SavedSearch:
    item = SavedSearch(user_id=user_id, name=name, filters=filters, notify=True)
    session.add(item)
    await session.flush()
    return item


async def list_saved_searches(session: AsyncSession, user_id: int) -> list[SavedSearch]:
    result = await session.execute(
        select(SavedSearch).where(SavedSearch.user_id == user_id).order_by(SavedSearch.id.desc())
    )
    return list(result.scalars().all())


async def get_saved_search(session: AsyncSession, search_id: int) -> SavedSearch | None:
    return await session.get(SavedSearch, search_id)


async def delete_saved_search(session: AsyncSession, search_id: int) -> None:
    item = await session.get(SavedSearch, search_id)
    if item:
        await session.delete(item)
        await session.flush()


async def all_notifying_searches(session: AsyncSession) -> list[SavedSearch]:
    result = await session.execute(
        select(SavedSearch).join(User).where(
            SavedSearch.notify.is_(True), User.notifications_enabled.is_(True)
        )
    )
    return list(result.scalars().all())


# ---------------- Inquiries ----------------

async def create_inquiry(
    session: AsyncSession, listing_id: int, from_user_id: int, **kwargs: Any
) -> Inquiry:
    item = Inquiry(listing_id=listing_id, from_user_id=from_user_id, **kwargs)
    session.add(item)
    await session.flush()
    return item


async def get_inquiry(session: AsyncSession, inquiry_id: int) -> Inquiry | None:
    return await session.get(Inquiry, inquiry_id)


async def list_inquiries_for_owner(session: AsyncSession, owner_id: int) -> list[Inquiry]:
    result = await session.execute(
        select(Inquiry)
        .join(Listing, Listing.id == Inquiry.listing_id)
        .where(Listing.user_id == owner_id)
        .order_by(Inquiry.id.desc())
    )
    return list(result.scalars().all())


async def list_all_inquiries(session: AsyncSession, limit: int = 50) -> list[Inquiry]:
    result = await session.execute(select(Inquiry).order_by(Inquiry.id.desc()).limit(limit))
    return list(result.scalars().all())


# ---------------- Contact requests ----------------

async def create_contact_request(
    session: AsyncSession,
    listing_id: int,
    inquiry_id: int | None,
    owner_id: int,
    requester_id: int,
    requester_consent: bool,
) -> ContactRequest:
    item = ContactRequest(
        listing_id=listing_id,
        inquiry_id=inquiry_id,
        owner_id=owner_id,
        requester_id=requester_id,
        requester_consent=requester_consent,
        owner_consent=False,
    )
    session.add(item)
    await session.flush()
    return item


async def get_contact_request(session: AsyncSession, request_id: int) -> ContactRequest | None:
    return await session.get(ContactRequest, request_id)


async def list_pending_contacts(session: AsyncSession, owner_id: int) -> list[ContactRequest]:
    result = await session.execute(
        select(ContactRequest).where(
            ContactRequest.owner_id == owner_id,
            ContactRequest.status == "PENDING",
        )
    )
    return list(result.scalars().all())


# ---------------- Viewings ----------------

async def create_viewing(
    session: AsyncSession,
    listing_id: int,
    owner_id: int,
    requester_id: int,
    visit_date: str,
    visit_time: str,
    note: str | None,
) -> ViewingRequest:
    item = ViewingRequest(
        listing_id=listing_id,
        owner_id=owner_id,
        requester_id=requester_id,
        visit_date=visit_date,
        visit_time=visit_time,
        note=note,
    )
    session.add(item)
    await session.flush()
    return item


async def get_viewing(session: AsyncSession, viewing_id: int) -> ViewingRequest | None:
    return await session.get(ViewingRequest, viewing_id)


async def list_viewings(session: AsyncSession, user_id: int) -> list[ViewingRequest]:
    result = await session.execute(
        select(ViewingRequest)
        .where(
            (ViewingRequest.requester_id == user_id) | (ViewingRequest.owner_id == user_id)
        )
        .order_by(ViewingRequest.id.desc())
    )
    return list(result.scalars().all())


async def list_all_viewings(session: AsyncSession, limit: int = 50) -> list[ViewingRequest]:
    result = await session.execute(
        select(ViewingRequest).order_by(ViewingRequest.id.desc()).limit(limit)
    )
    return list(result.scalars().all())


# ---------------- Reports ----------------

async def create_report(
    session: AsyncSession,
    reporter_id: int,
    listing_id: int | None,
    reason: str,
    details: str | None,
) -> Report:
    item = Report(
        reporter_id=reporter_id,
        listing_id=listing_id,
        reason=reason,
        details=details,
    )
    session.add(item)
    await session.flush()
    return item


async def get_report(session: AsyncSession, report_id: int) -> Report | None:
    return await session.get(Report, report_id)


async def list_reports(session: AsyncSession, open_only: bool = True) -> list[Report]:
    query = select(Report)
    if open_only:
        query = query.where(Report.status == ReportStatus.OPEN)
    result = await session.execute(query.order_by(Report.id.desc()))
    return list(result.scalars().all())


# ---------------- Notifications ----------------

async def create_notification(
    session: AsyncSession, user_id: int, code: str, payload: dict[str, Any] | None = None
) -> Notification:
    item = Notification(user_id=user_id, code=code, payload=payload or {})
    session.add(item)
    await session.flush()
    return item


async def list_notifications(session: AsyncSession, user_id: int, limit: int = 30) -> list[Notification]:
    result = await session.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def unread_count(session: AsyncSession, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
        )
        or 0
    )


async def mark_all_read(session: AsyncSession, user_id: int) -> None:
    notifications = (
        await session.execute(
            select(Notification).where(
                Notification.user_id == user_id, Notification.is_read.is_(False)
            )
        )
    ).scalars().all()
    for item in notifications:
        item.is_read = True
    await session.flush()


# ---------------- Admin ----------------

async def add_moderation_log(
    session: AsyncSession,
    admin_id: int,
    action: str,
    listing_id: int | None = None,
    target_user_id: int | None = None,
    reason: str | None = None,
) -> ModerationLog:
    item = ModerationLog(
        admin_id=admin_id,
        action=action,
        listing_id=listing_id,
        target_user_id=target_user_id,
        reason=reason,
    )
    session.add(item)
    await session.flush()
    return item


async def list_moderation_logs(session: AsyncSession, limit: int = 30) -> list[ModerationLog]:
    result = await session.execute(
        select(ModerationLog).order_by(ModerationLog.id.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def add_search_log(
    session: AsyncSession,
    user_id: int | None,
    property_type_id: int | None = None,
    region_id: int | None = None,
    query: str | None = None,
) -> None:
    session.add(
        SearchLog(
            user_id=user_id,
            property_type_id=property_type_id,
            region_id=region_id,
            query=query,
        )
    )
    await session.flush()


async def top_search_types(session: AsyncSession, since: datetime, limit: int = 5) -> list[tuple[str, int]]:
    from database.models import PropertyType

    result = await session.execute(
        select(SearchLog.property_type_id, func.count(SearchLog.id))
        .where(SearchLog.created_at >= since, SearchLog.property_type_id.is_not(None))
        .group_by(SearchLog.property_type_id)
        .order_by(func.count(SearchLog.id).desc())
        .limit(limit)
    )
    rows = []
    for type_id, count in result.all():
        ptype = await session.get(PropertyType, type_id)
        rows.append((ptype.name_uz if ptype else str(type_id), int(count)))
    return rows


async def create_broadcast(
    session: AsyncSession, admin_id: int, segment: str, message: str, recipients: int
) -> Broadcast:
    item = Broadcast(
        admin_id=admin_id, segment=segment, message=message, recipients=recipients
    )
    session.add(item)
    await session.flush()
    return item
