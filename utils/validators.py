from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

_PHONE_RE = re.compile(r"[^\d]")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    digits = _PHONE_RE.sub("", value)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) == 9:
        digits = "998" + digits
    return digits


def is_valid_phone(value: str | None) -> bool:
    digits = normalize_phone(value)
    return 9 <= len(digits) <= 15


def parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip().replace(" ", "").replace(",", "")
    if cleaned in {"", "-", "0"}:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_int_list(value: str | None) -> list[int]:
    if not value:
        return []
    result: list[int] = []
    for part in re.split(r"[,\s]+", value.strip()):
        number = parse_int(part)
        if number is not None and number > 0:
            result.append(number)
    return result


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    cleaned = (
        value.strip()
        .replace(" ", "")
        .replace(",", ".")
        .replace("so'm", "")
        .replace("сум", "")
        .strip()
    )
    if not cleaned:
        return None
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None
    return number if number > 0 else None


def parse_float(value: str | None) -> float | None:
    number = parse_decimal(value)
    return float(number) if number is not None else None


def parse_date(value: str | None) -> date | None:
    if not value or not _DATE_RE.match(value.strip()):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def parse_time(value: str | None) -> str | None:
    if not value:
        return None
    match = _TIME_RE.match(value.strip())
    if not match:
        return None
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def clean_text(value: str | None, max_length: int = 2000) -> str:
    if not value:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value).strip()
    return text[:max_length]


def is_valid_year(value: int | None) -> bool:
    return value is not None and 1900 <= value <= 2030
