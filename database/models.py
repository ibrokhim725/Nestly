from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
   Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UserStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    DELETED = "DELETED"


class ProfileType(StrEnum):
    OWNER = "OWNER"
    AGENT = "AGENT"
    DEVELOPER = "DEVELOPER"


class ListingType(StrEnum):
    SALE = "SALE"
    RENT = "RENT"
    DAILY = "DAILY"
    COMMERCIAL_SALE = "COMMERCIAL_SALE"
    COMMERCIAL_RENT = "COMMERCIAL_RENT"
    LAND_SALE = "LAND_SALE"


class ListingStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    SOLD = "SOLD"
    RENTED = "RENTED"
    HIDDEN = "HIDDEN"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"


class PriceUnit(StrEnum):
    TOTAL = "TOTAL"
    MONTH = "MONTH"
    DAY = "DAY"


class InquiryStatus(StrEnum):
    PENDING = "PENDING"
    REPLIED = "REPLIED"
    DECLINED = "DECLINED"


class ContactStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class ViewingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    RESCHEDULED = "RESCHEDULED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


class ReportReason(StrEnum):
    FAKE = "FAKE"
    WRONG_PRICE = "WRONG_PRICE"
    OTHER_PHOTO = "OTHER_PHOTO"
    WRONG_INFO = "WRONG_INFO"
    SUSPICIOUS_USER = "SUSPICIOUS_USER"
    OTHER = "OTHER"


class ReportStatus(StrEnum):
    OPEN = "OPEN"
    REVIEWED = "REVIEWED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ModerationAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_FIX = "REQUEST_FIX"
    MARK_SUSPICIOUS = "MARK_SUSPICIOUS"
    WARN = "WARN"
    BLOCK = "BLOCK"
    UNBLOCK = "UNBLOCK"
    BROADCAST = "BROADCAST"
    DELETE_PROFILE = "DELETE_PROFILE"
    REPORT_RESOLVED = "REPORT_RESOLVED"
    REPORT_DISMISSED = "REPORT_DISMISSED"
    REGION_ADD = "REGION_ADD"
    DISTRICT_ADD = "DISTRICT_ADD"


class ConsentType(StrEnum):
    TERMS = "TERMS"
    PRIVACY = "PRIVACY"
    PHONE_SHARE = "PHONE_SHARE"
    CONTACT_SHARE = "CONTACT_SHARE"


def _enum(enum_cls: type[StrEnum]) -> Any:
    return Enum(enum_cls, native_enum=False, values_callable=lambda x: [e.value for e in x])


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id", unique=True),
        Index("ix_users_status", "status"),
        Index("ix_users_last_active", "last_active_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="uz", nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        _enum(UserStatus), default=UserStatus.PENDING, nullable=False
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    listings: Mapped[list["Listing"]] = relationship(back_populates="owner")
    favorites: Mapped[list["Favorite"]] = relationship(back_populates="user")
    saved_searches: Mapped[list["SavedSearch"]] = relationship(back_populates="user")
    consents: Mapped[list["UserConsent"]] = relationship(back_populates="user")

    @property
    def first_name(self) -> str:
        return self.profile.first_name if self.profile else ""

    @property
    def last_name(self) -> str:
        return self.profile.last_name if self.profile else ""

    @property
    def phone(self) -> str:
        return self.profile.phone if self.profile else ""

    @property
    def profile_type(self) -> ProfileType | None:
        return self.profile.profile_type if self.profile else None

    @property
    def is_phone_verified(self) -> bool:
        return bool(self.profile and self.profile.is_phone_verified)

    @property
    def is_profile_verified(self) -> bool:
        return bool(self.profile and self.profile.is_profile_verified)

    @property
    def is_documents_verified(self) -> bool:
        return bool(self.profile and self.profile.is_documents_verified)

    @property
    def display_name(self) -> str:
        return " ".join(filter(None, [self.first_name, self.last_name])) or (
            f"@{self.username}" if self.username else str(self.telegram_id)
        )

    @property
    def is_active_user(self) -> bool:
        return self.status == UserStatus.ACTIVE


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"
    __table_args__ = (Index("ix_user_profiles_user_id", "user_id", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    avatar_file_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    profile_type: Mapped[ProfileType] = mapped_column(
        _enum(ProfileType), default=ProfileType.OWNER, nullable=False
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_phone_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_profile_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_documents_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="profile")


class PropertyType(Base, TimestampMixin):
    __tablename__ = "property_types"
    __table_args__ = (UniqueConstraint("code", name="uq_property_types_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    listings: Mapped[list["Listing"]] = relationship(back_populates="property_type")


class Region(Base, TimestampMixin):
    __tablename__ = "regions"
    __table_args__ = (UniqueConstraint("code", name="uq_regions_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name_uz: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    districts: Mapped[list["District"]] = relationship(back_populates="region")
    listings: Mapped[list["Listing"]] = relationship(back_populates="region")


class District(Base, TimestampMixin):
    __tablename__ = "districts"
    __table_args__ = (
        UniqueConstraint("region_id", "name_uz", name="uq_districts_region_name"),
        Index("ix_districts_region_id", "region_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False
    )
    name_uz: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    region: Mapped["Region"] = relationship(back_populates="districts")
    neighborhoods: Mapped[list["Neighborhood"]] = relationship(back_populates="district")
    listings: Mapped[list["Listing"]] = relationship(back_populates="district")


class Neighborhood(Base, TimestampMixin):
    __tablename__ = "neighborhoods"
    __table_args__ = (
        UniqueConstraint("district_id", "name_uz", name="uq_neighborhoods_district_name"),
        Index("ix_neighborhoods_district_id", "district_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False
    )
    name_uz: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)

    district: Mapped["District"] = relationship(back_populates="neighborhoods")
    listings: Mapped[list["Listing"]] = relationship(back_populates="neighborhood")


class Listing(Base, TimestampMixin):
    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listings_status", "status"),
        Index("ix_listings_user_id", "user_id"),
        Index("ix_listings_region_district", "region_id", "district_id"),
        Index("ix_listings_price", "price"),
        Index("ix_listings_type", "listing_type"),
        Index("ix_listings_expires_at", "expires_at"),
        Index("ix_listings_title", "title"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    listing_type: Mapped[ListingType] = mapped_column(_enum(ListingType), nullable=False)
    property_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("property_types.id"), nullable=False
    )
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id"), nullable=False)
    district_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("districts.id"), nullable=False
    )
    neighborhood_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("neighborhoods.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Any] = mapped_column(Numeric(18, 2), nullable=False)
    price_unit: Mapped[PriceUnit] = mapped_column(
        _enum(PriceUnit), default=PriceUnit.TOTAL, nullable=False
    )
    area: Mapped[Any] = mapped_column(Numeric(10, 2), nullable=False)
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    built_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    renovation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    furnished: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_family_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_student_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_long_term: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_deposit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    utilities_terms: Mapped[str | None] = mapped_column(String(32), nullable=True)
    guests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amenities: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    latitude: Mapped[Any] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Any] = mapped_column(Numeric(10, 7), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    status: Mapped[ListingStatus] = mapped_column(
        _enum(ListingStatus), default=ListingStatus.DRAFT, nullable=False
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner: Mapped["User"] = relationship(back_populates="listings")
    property_type: Mapped["PropertyType"] = relationship(back_populates="listings")
    region: Mapped["Region"] = relationship(back_populates="listings")
    district: Mapped["District"] = relationship(back_populates="listings")
    neighborhood: Mapped["Neighborhood"] = relationship(back_populates="listings")
    images: Mapped[list["ListingImage"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="ListingImage.position"
    )
    videos: Mapped[list["ListingVideo"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
    favorites: Mapped[list["Favorite"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class ListingImage(Base):
    __tablename__ = "listing_images"
    __table_args__ = (Index("ix_listing_images_listing_id", "listing_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    listing: Mapped["Listing"] = relationship(back_populates="images")


class ListingVideo(Base):
    __tablename__ = "listing_videos"
    __table_args__ = (Index("ix_listing_videos_listing_id", "listing_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    listing: Mapped["Listing"] = relationship(back_populates="videos")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),
        Index("ix_favorites_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="favorites")
    listing: Mapped["Listing"] = relationship(back_populates="favorites")


class SavedSearch(Base, TimestampMixin):
    __tablename__ = "saved_searches"
    __table_args__ = (Index("ix_saved_searches_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notify: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="saved_searches")


class Inquiry(Base, TimestampMixin):
    __tablename__ = "inquiries"
    __table_args__ = (
        Index("ix_inquiries_listing_id", "listing_id"),
        Index("ix_inquiries_from_user_id", "from_user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    from_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    phone_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[InquiryStatus] = mapped_column(
        _enum(InquiryStatus), default=InquiryStatus.PENDING, nullable=False
    )
    reply_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ContactRequest(Base, TimestampMixin):
    __tablename__ = "contact_requests"
    __table_args__ = (
        Index("ix_contact_requests_owner_id", "owner_id"),
        Index("ix_contact_requests_requester_id", "requester_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    inquiry_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("inquiries.id", ondelete="SET NULL"), nullable=True
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requester_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requester_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[ContactStatus] = mapped_column(
        _enum(ContactStatus), default=ContactStatus.PENDING, nullable=False
    )


class ViewingRequest(Base, TimestampMixin):
    __tablename__ = "viewing_requests"
    __table_args__ = (
        Index("ix_viewing_requests_owner_id", "owner_id"),
        Index("ix_viewing_requests_requester_id", "requester_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requester_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    visit_date: Mapped[str] = mapped_column(String(10), nullable=False)
    visit_time: Mapped[str] = mapped_column(String(5), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    proposed_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    status: Mapped[ViewingStatus] = mapped_column(
        _enum(ViewingStatus), default=ViewingStatus.PENDING, nullable=False
    )


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Report(Base, TimestampMixin):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_status", "status"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    listing_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True
    )
    reporter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[ReportReason] = mapped_column(_enum(ReportReason), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        _enum(ReportStatus), default=ReportStatus.OPEN, nullable=False
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModerationLog(Base):
    __tablename__ = "moderation_logs"
    __table_args__ = (Index("ix_moderation_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    listing_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("listings.id", ondelete="SET NULL"), nullable=True
    )
    target_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[ModerationAction] = mapped_column(_enum(ModerationAction), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserBlock(Base, TimestampMixin):
    __tablename__ = "user_blocks"
    __table_args__ = (Index("ix_user_blocks_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"
    __table_args__ = (Index("ix_admin_users_telegram_id", "telegram_id", unique=True),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserConsent(Base):
    __tablename__ = "user_consents"
    __table_args__ = (
        UniqueConstraint("user_id", "consent_type", name="uq_user_consents_user_type"),
        Index("ix_user_consents_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    consent_type: Mapped[ConsentType] = mapped_column(_enum(ConsentType), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="consents")


class SearchLog(Base):
    __tablename__ = "search_logs"
    __table_args__ = (Index("ix_search_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    property_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    region_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    query: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Broadcast(Base, TimestampMixin):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    segment: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recipients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
