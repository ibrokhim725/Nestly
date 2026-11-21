from utils.pagination import normalize_page, paginate, total_pages


def test_total_pages() -> None:
    assert total_pages(0) == 1
    assert total_pages(5, 5) == 1
    assert total_pages(6, 5) == 2
    assert total_pages(11, 5) == 3


def test_paginate() -> None:
    items = list(range(1, 13))
    assert paginate(items, 1, 5) == [1, 2, 3, 4, 5]
    assert paginate(items, 3, 5) == [11, 12]
    assert paginate(items, 0, 5) == [1, 2, 3, 4, 5]


def test_normalize_page() -> None:
    assert normalize_page(0, 12, 5) == 1
    assert normalize_page(99, 12, 5) == 3
    assert normalize_page(2, 12, 5) == 2
