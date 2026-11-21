from types import SimpleNamespace

from config import settings
from keyboards.inline import (
    AdminCB,
    ViewCB,
    admin_menu_kb,
    districts_kb,
    main_menu_kb,
    moderation_kb,
    viewing_actions_kb,
)
from utils.i18n import make_i18n

I18N = make_i18n(settings.locales_dir, "uz")


def test_callback_pack_roundtrip() -> None:
    packed = AdminCB(action="warn", value="42").pack()
    assert packed.startswith("adm:")
    unpacked = AdminCB.unpack(packed)
    assert unpacked.action == "warn"
    assert unpacked.value == "42"

    view = ViewCB.unpack(ViewCB(action="confirm", id=7).pack())
    assert view.action == "confirm"
    assert view.id == 7


def test_keyboards_build() -> None:
    for markup in (
        admin_menu_kb(I18N),
        main_menu_kb(I18N, is_admin=True),
        moderation_kb(I18N, 1),
        viewing_actions_kb(I18N, 1),
    ):
        assert markup is not None
        assert getattr(markup, "inline_keyboard", None) or getattr(markup, "keyboard", None)


def test_districts_kb_search_has_all_districts_button() -> None:
    district = SimpleNamespace(id=7, name_uz="Yunusobod", name_ru="Юнусабад")
    search_callbacks = [
        button.callback_data
        for row in districts_kb(I18N, [district]).inline_keyboard
        for button in row
    ]
    listing_callbacks = [
        button.callback_data
        for row in districts_kb(I18N, [district], scope="cancel").inline_keyboard
        for button in row
    ]
    assert "ds:7" in search_callbacks
    assert any(item.startswith("fl:skip_district") for item in search_callbacks)
    assert not any("skip_district" in item for item in listing_callbacks)
