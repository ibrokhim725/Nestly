from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")

    database_url: str = Field(
        default="postgresql+asyncpg://uytop:uytop@localhost:5432/uytop",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    mode: str = Field(default="polling", alias="MODE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    webhook_url: str = Field(default="", alias="WEBHOOK_URL")
    webhook_path: str = Field(default="/webhook", alias="WEBHOOK_PATH")
    webhook_host: str = Field(default="0.0.0.0", alias="WEBHOOK_HOST")
    webhook_port: int = Field(default=8000, alias="WEBHOOK_PORT")
    webhook_secret: str = Field(default="uytop-secret", alias="WEBHOOK_SECRET")

    listing_ttl_days: int = Field(default=30, alias="LISTING_TTL_DAYS")
    expiry_reminder_days: int = Field(default=3, alias="EXPIRY_REMINDER_DAYS")
    min_listing_images: int = Field(default=3, alias="MIN_LISTING_IMAGES")
    max_listing_images: int = Field(default=15, alias="MAX_LISTING_IMAGES")
    max_active_listings_per_user: int = Field(
        default=20, alias="MAX_ACTIVE_LISTINGS_PER_USER"
    )
    rate_limit_seconds: float = Field(default=1.0, alias="RATE_LIMIT_SECONDS")

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"polling", "webhook"}:
            return "polling"
        return value

    @property
    def admin_ids(self) -> set[int]:
        result: set[int] = set()
        for part in self.admin_ids_raw.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit():
                result.add(int(part))
        return result

    @property
    def root_dir(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def locales_dir(self) -> Path:
        return self.root_dir / "locales"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
