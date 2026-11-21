from datetime import date
from decimal import Decimal

from utils.validators import (
    clean_text,
    is_valid_phone,
    normalize_phone,
    parse_date,
    parse_decimal,
    parse_int,
    parse_int_list,
    parse_time,
)


def test_normalize_phone() -> None:
    assert normalize_phone("+998 (90) 123-45-67") == "998901234567"
    assert normalize_phone("901234567") == "998901234567"
    assert normalize_phone("") == ""
    assert normalize_phone(None) == ""


def test_is_valid_phone() -> None:
    assert is_valid_phone("+998901234567") is True
    assert is_valid_phone("12") is False
    assert is_valid_phone(None) is False


def test_parse_int() -> None:
    assert parse_int("1 234") == 1234
    assert parse_int("0") is None
    assert parse_int("-") is None
    assert parse_int(None) is None
    assert parse_int("abc") is None


def test_parse_int_list() -> None:
    assert parse_int_list("1, 2 3") == [1, 2, 3]
    assert parse_int_list("0 -5") == []
    assert parse_int_list(None) == []


def test_parse_decimal() -> None:
    assert parse_decimal("1,5") == Decimal("1.5")
    assert parse_decimal("1 000 so'm") == Decimal("1000")
    assert parse_decimal("abc") is None
    assert parse_decimal("0") is None


def test_parse_date_and_time() -> None:
    assert parse_date("2026-01-05") == date(2026, 1, 5)
    assert parse_date("05.01.2026") is None
    assert parse_time("9:05") == "09:05"
    assert parse_time("25:00") is None
    assert parse_time(None) is None


def test_clean_text() -> None:
    assert clean_text("  hello\x00  ") == "hello"
    assert clean_text("abcdef", max_length=3) == "abc"
    assert clean_text(None) == ""
