from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import Update
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import AsyncSessionLocal

Handler = Callable[[Update, dict[str, Any]], Awaitable[Any]]


class DatabaseMiddleware:
    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]) -> Any:
        async with AsyncSessionLocal() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


def session_provider() -> AsyncSession:
    return AsyncSessionLocal()
