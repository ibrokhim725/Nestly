from __future__ import annotations

from typing import Any

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from keyboards.reply import contact_kb, main_menu_kb
from keyboards.inline import language_kb

Event = Message | CallbackQuery


class MenuTextFilter(BaseFilter):
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, message: Message, i18n: Any) -> bool:
        return message.text == i18n.t(self.key)


class StateIn(BaseFilter):
    def __init__(self, states):
        self.states = set(states)

    async def __call__(self, event, state) -> bool:
        return await state.get_state() in self.states


class StateDataHas(BaseFilter):
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, event, state) -> bool:
        data = await state.get_data()
        return self.key in data


def target_message(event: Event) -> Message | None:
    if isinstance(event, CallbackQuery):
        return event.message
    return event


async def answer(event: Event, text: str, **kwargs: Any) -> Message | None:
    message = target_message(event)
    if message is None:
        return None
    return await message.answer(text, **kwargs)


async def edit(event: Event, text: str, **kwargs: Any) -> Message | None:
    message = target_message(event)
    if message is None:
        return None
    try:
        return await message.edit_text(text, **kwargs)
    except Exception:
        return await message.answer(text, **kwargs)


def registered(user: Any | None) -> bool:
    if user is None or user.status is None:
        return False
    return str(getattr(user.status, "value", user.status)) in {"ACTIVE"}


async def require_user(event: Event, user: Any | None, i18n: Any) -> bool:
    if user is not None and str(getattr(user.status, "value", user.status)) == "ACTIVE":
        return True
    if isinstance(event, CallbackQuery):
        try:
            await event.answer(i18n.t("registration.intro"), show_alert=False)
        except Exception:
            pass
    await answer(
        event,
        i18n.t("registration.intro"),
        reply_markup=language_kb() if user is None else contact_kb(i18n),
    )
    return False


async def require_admin(event: Event, data: dict[str, Any], i18n: Any) -> bool:
    if data.get("is_admin"):
        return True
    if isinstance(event, CallbackQuery):
        try:
            await event.answer(i18n.t("common.access_denied"), show_alert=True)
        except Exception:
            pass
    else:
        await answer(event, i18n.t("common.access_denied"))
    return False


def menu_markup(i18n: Any, is_admin: bool = False):
    return main_menu_kb(i18n, is_admin)
