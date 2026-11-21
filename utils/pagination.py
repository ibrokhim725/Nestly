from __future__ import annotations

from typing import Sequence, TypeVar

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 5
SEARCH_PAGE_SIZE = 10


def paginate(items: Sequence[T], page: int, page_size: int = DEFAULT_PAGE_SIZE) -> list[T]:
    if page < 1:
        page = 1
    start = (page - 1) * page_size
    return list(items[start : start + page_size])


def total_pages(total: int, page_size: int = DEFAULT_PAGE_SIZE) -> int:
    if total <= 0:
        return 1
    return (total + page_size - 1) // page_size


def normalize_page(page: int, total: int, page_size: int = DEFAULT_PAGE_SIZE) -> int:
    pages = total_pages(total, page_size)
    return max(1, min(page, pages))
