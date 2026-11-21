from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Update
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.repositories import users as user_repo
from utils.i18n import I18n, make_i18n

Handler = Callable[[Update, dict[str, Any]], Awaitable[Any]]


def event_from_user(event: Update) -> Any | None:
    inner = event.event if isinstance(event, Update) else event
    return getattr(inner, "from_user", None)


class UserContextMiddleware:
    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]) -> Any:
        session: AsyncSession | None = data.get("session")
        from_user = event_from_user(event)
        user = None
        if session is not None and from_user is not None:
            try:
                user = await user_repo.get_by_telegram(session, from_user.id)
                if user:
                    await user_repo.touch(session, user)
            except Exception:
                user = None

        language = user.language if user else "uz"
        data["user"] = user
        data["i18n"] = make_i18n(settings.locales_dir, language)
        data["is_admin"] = bool(
            from_user and from_user.id in settings.admin_ids
        )
        return await handler(event, data)
