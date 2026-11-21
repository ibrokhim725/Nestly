from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram.types import CallbackQuery, Update

from config import settings

Handler = Callable[[Update, dict[str, Any]], Awaitable[Any]]

_last_calls: dict[int, float] = {}
_lock = asyncio.Lock()


def _event_from_user(event: Update) -> Any | None:
    inner = event.event if isinstance(event, Update) else event
    return getattr(inner, "from_user", None)


class ThrottlingMiddleware:
    def __init__(self, seconds: float | None = None):
        self.seconds = settings.rate_limit_seconds if seconds is None else seconds

    async def __call__(self, handler: Handler, event: Update, data: dict[str, Any]) -> Any:
        from_user = _event_from_user(event)
        if not from_user or self.seconds <= 0:
            return await handler(event, data)

        user_id = from_user.id
        now = time.monotonic()
        async with _lock:
            last = _last_calls.get(user_id, 0.0)
            if now - last < self.seconds:
                allowed = False
            else:
                _last_calls[user_id] = now
                allowed = True
            if len(_last_calls) > 10000:
                for key, value in list(_last_calls.items()):
                    if now - value > 60:
                        _last_calls.pop(key, None)

        if allowed:
            return await handler(event, data)

        inner = event.event if isinstance(event, Update) else event
        if isinstance(inner, CallbackQuery):
            try:
                await inner.answer("⏳", show_alert=False)
            except Exception:
                pass
        return None
