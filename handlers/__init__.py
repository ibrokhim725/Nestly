from __future__ import annotations

from aiogram import Dispatcher

from handlers import (
    admin,
    appointments,
    favorites,
    interactions,
    listing,
    menu,
    notifications,
    profile,
    registration,
    search,
    start,
)

MODULES = (
    start,
    registration,
    admin,
    menu,
    favorites,
    listing,
    search,
    profile,
    interactions,
    notifications,
    appointments,
)


def setup_routers(dispatcher: Dispatcher) -> None:
    for module in MODULES:
        dispatcher.include_router(module.router)


__all__ = ["setup_routers", "MODULES"]
