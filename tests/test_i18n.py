import json
from pathlib import Path

from config import settings
from utils.i18n import make_i18n, normalize_language


def _flat(data: dict, prefix: str = "") -> set[str]:
    result: set[str] = set()
    for key, value in data.items():
        full = f"{prefix}{key}"
        if isinstance(value, dict):
            result |= _flat(value, full + ".")
        else:
            result.add(full)
    return result


def test_normalize_language() -> None:
    assert normalize_language("ru-RU") == "ru"
    assert normalize_language("UZ") == "uz"
    assert normalize_language(None) == "uz"
    assert normalize_language("en") == "uz"


def test_translation_lookup() -> None:
    i18n = make_i18n(settings.locales_dir, "uz")
    assert i18n.t("common.yes")
    assert i18n.t("missing.key.here") == "missing.key.here"


def test_translation_formatting() -> None:
    i18n = make_i18n(settings.locales_dir, "uz")
    assert i18n.t("notifications.unread", count=3).endswith("3")


def test_locale_key_parity() -> None:
    base = Path(settings.locales_dir)
    uz = _flat(json.loads((base / "uz.json").read_text(encoding="utf-8")))
    ru = _flat(json.loads((base / "ru.json").read_text(encoding="utf-8")))
    assert uz == ru
