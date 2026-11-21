from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from config import settings
from utils.formatters import (
    format_date,
    format_listing_card,
    format_price,
    price_label,
)
from utils.i18n import make_i18n

UZ = make_i18n(settings.locales_dir, "uz")
RU = make_i18n(settings.locales_dir, "ru")


def test_format_price() -> None:
    assert format_price(Decimal("1500000"), UZ) == "1 500 000 so'm"
    assert format_price(1000, RU) == "1 000 сум"
    assert format_price(None, UZ) == "—"


def test_format_date() -> None:
    assert format_date(date(2026, 1, 5)) == "05.01.2026"
    assert format_date(datetime(2026, 1, 5, 10, 30)) == "05.01.2026"
    assert format_date(None) == "—"


def test_price_label() -> None:
    assert price_label("month", UZ) == UZ.t("price_unit.month")


def test_format_listing_card() -> None:
    listing = SimpleNamespace(
        title="Test <house>",
        region=SimpleNamespace(name_uz="Toshkent", name_ru="Ташкент"),
        district=None,
        price=Decimal("2000000"),
        price_unit="TOTAL",
        rooms=3,
        area=Decimal("60.5"),
        floor=2,
        total_floors=5,
        condition="new",
        furnished=True,
        status="ACTIVE",
        created_at=datetime(2026, 1, 5),
    )
    text = format_listing_card(listing, UZ)
    assert "Test &lt;house&gt;" in text
    assert "3" in text
    assert UZ.t("listing_status.ACTIVE") in text
