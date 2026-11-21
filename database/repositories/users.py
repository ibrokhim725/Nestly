from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    ProfileType,
    User,
    UserBlock,
    UserConsent,
    UserProfile,
    UserStatus,
)
from utils.validators import normalize_phone


def _load_user(query):
    return query.options(selectinload(User.profile))


async def get_by_telegram(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(
        _load_user(select(User)).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(_load_user(select(User)).where(User.id == user_id))
    return result.scalar_one_or_none()


async def find_by_phone(session: AsyncSession, phone: str, exclude_user_id: int = 0) -> User | None:
    digits = normalize_phone(phone)
    if not digits:
        return None
    result = await session.execute(
        _load_user(select(User))
        .join(UserProfile)
        .where(UserProfile.phone == digits, User.id != exclude_user_id)
    )
    return result.scalars().first()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    language: str,
) -> User:
    user = User(
        telegram_id=telegram_id,
        username=username,
        language=language,
        status=UserStatus.PENDING,
    )
    user.profile = UserProfile(
        first_name="",
        last_name="",
        phone="",
        profile_type=ProfileType.OWNER,
        terms_accepted=False,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user, ["profile"])
    return user


async def complete_registration(
    session: AsyncSession,
    user: User,
    first_name: str,
    last_name: str,
    phone: str,
    profile_type: ProfileType,
) -> User:
    user.profile.first_name = first_name
    user.profile.last_name = last_name
    user.profile.phone = normalize_phone(phone)
    user.profile.profile_type = profile_type
    user.profile.terms_accepted = True
    user.profile.is_phone_verified = True
    user.status = UserStatus.ACTIVE
    user.last_active_at = datetime.now(timezone.utc)
    session.add(
        UserConsent(
            user_id=user.id,
            consent_type="TERMS",
            accepted=True,
            text="terms_accepted",
        )
    )
    session.add(
        UserConsent(
            user_id=user.id,
            consent_type="PHONE_SHARE",
            accepted=True,
            text="verified_via_telegram_contact",
        )
    )
    await session.flush()
    return user


async def set_language(session: AsyncSession, user: User, language: str) -> None:
    user.language = language
    await session.flush()


async def touch(session: AsyncSession, user: User) -> None:
    user.last_active_at = datetime.now(timezone.utc)
    await session.flush()


async def set_notifications(session: AsyncSession, user: User, enabled: bool) -> None:
    user.notifications_enabled = enabled
    await session.flush()


async def set_status(session: AsyncSession, user: User, status: UserStatus) -> None:
    user.status = status
    await session.flush()


async def count_users(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count(User.id))) or 0)


async def count_new_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(select(func.count(User.id)).where(User.created_at >= since)) or 0
    )


async def count_active_users(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count(User.id)).where(User.last_active_at >= since)
        )
        or 0
    )


async def list_users(session: AsyncSession, limit: int = 20, offset: int = 0) -> list[User]:
    result = await session.execute(
        _load_user(select(User)).order_by(User.id.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def find_users(session: AsyncSession, query: str, limit: int = 10) -> list[User]:
    pattern = f"%{query.strip()}%"
    result = await session.execute(
        _load_user(select(User))
        .outerjoin(UserProfile)
        .where(
            cast(User.telegram_id, String).like(pattern)
            | User.username.ilike(pattern)
            | UserProfile.phone.like(pattern)
            | UserProfile.first_name.ilike(pattern)
        )
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_active_block(session: AsyncSession, user_id: int) -> UserBlock | None:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(UserBlock).where(
            UserBlock.user_id == user_id,
            UserBlock.is_active.is_(True),
            (UserBlock.expires_at.is_(None)) | (UserBlock.expires_at > now),
        )
    )
    return result.scalars().first()


async def create_block(
    session: AsyncSession,
    user_id: int,
    admin_id: int,
    reason: str | None,
    permanent: bool = True,
    days: int | None = None,
) -> UserBlock:
    expires_at = None
    if not permanent and days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    block = UserBlock(
        user_id=user_id,
        admin_id=admin_id,
        reason=reason,
        is_permanent=permanent,
        expires_at=expires_at,
        is_active=True,
    )
    session.add(block)
    user = await get_by_id(session, user_id)
    if user:
        user.status = UserStatus.BLOCKED
    await session.flush()
    return block


async def unblock_user(session: AsyncSession, user_id: int) -> None:
    blocks = (
        await session.execute(select(UserBlock).where(UserBlock.user_id == user_id))
    ).scalars().all()
    for block in blocks:
        block.is_active = False
    user = await get_by_id(session, user_id)
    if user and user.status == UserStatus.BLOCKED:
        user.status = UserStatus.ACTIVE
    await session.flush()
