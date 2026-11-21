from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import services.search_service as search_service
from services.search_service import normalize_filters, serialize_filters


def test_normalize_filters_drops_empty() -> None:
    result = normalize_filters(
        {
            "region_id": "5",
            "min_price": "",
            "max_price": 0,
            "district_id": None,
            "floor": "3",
        }
    )
    assert result["region_id"] == 5
    assert result["floor"] == 3
    assert "min_price" not in result
    assert "max_price" not in result
    assert "district_id" not in result
    assert result["sort"] == "new"


def test_normalize_filters_rooms() -> None:
    assert normalize_filters({"rooms": "1, 2, 3"})["rooms"] == [1, 2, 3]
    assert normalize_filters({"rooms": 2})["rooms"] == [2]


def test_normalize_filters_invalid_number() -> None:
    result = normalize_filters({"min_price": "abc"})
    assert "min_price" not in result


def test_serialize_filters_decimal() -> None:
    result = serialize_filters({"min_price": Decimal("1000"), "sort": "cheap"})
    assert result["min_price"] == 1000
    assert result["sort"] == "cheap"


async def test_search_page_returns_ten_items(monkeypatch) -> None:
    items = [object() for _ in range(12)]
    monkeypatch.setattr(search_service, "search", AsyncMock(return_value=items))

    page, total = await search_service.search_page(MagicMock(), {"sort": "new"}, 1)

    assert len(page) == 10
    assert total == 12
