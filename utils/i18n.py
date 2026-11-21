from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LANGUAGES = ("uz", "ru")
DEFAULT_LANGUAGE = "uz"


def normalize_language(value: str | None) -> str:
    if not value:
        return DEFAULT_LANGUAGE
    value = value.lower().strip()
    if value.startswith("uz"):
        return "uz"
    if value.startswith("ru"):
        return "ru"
    return DEFAULT_LANGUAGE


@lru_cache
def load_locales(directory: str | Path) -> dict[str, dict[str, Any]]:
    base = Path(directory)
    result: dict[str, dict[str, Any]] = {}
    for lang in SUPPORTED_LANGUAGES:
        path = base / f"{lang}.json"
        with path.open("r", encoding="utf-8") as file:
            result[lang] = json.load(file)
    return result


class I18n:
    def __init__(self, lang: str, data: dict[str, Any]):
        self.lang = normalize_language(lang)
        self._data = data

    def t(self, key: str, **kwargs: Any) -> str:
        node: Any = self._data.get(self.lang, {})
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return key if not kwargs else key.format(**kwargs)
            node = node[part]
        if not isinstance(node, str):
            return key
        if kwargs:
            try:
                return node.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                return node
        return node

    def __call__(self, key: str, **kwargs: Any) -> str:
        return self.t(key, **kwargs)


def make_i18n(directory: str | Path, lang: str | None) -> I18n:
    data = load_locales(directory)
    return I18n(normalize_language(lang), data)
