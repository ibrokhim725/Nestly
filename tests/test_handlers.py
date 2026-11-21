from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import CallbackQuery, Chat, Message

from config import settings
from keyboards.inline import RegionCB
from states.profile import CommonFlow
from utils.i18n import make_i18n


def test_build_dispatcher() -> None:
    from main import build_dispatcher

    dispatcher = build_dispatcher()
    assert dispatcher is not None
    assert len(dispatcher.sub_routers) == 11


def test_common_flow_states() -> None:
    expected = {
        "viewing_date",
        "viewing_time",
        "viewing_note",
        "viewing_propose_date",
        "viewing_propose_time",
        "inquiry_name",
        "inquiry_purpose",
        "inquiry_message",
        "inquiry_phone",
        "report_details",
        "broadcast_message",
        "reject_reason",
        "fix_reason",
        "warning_message",
        "region_name_uz",
        "region_name_ru",
        "region_code",
        "district_region_id",
        "district_name_uz",
        "district_name_ru",
    }
    state_names = {state.state.split(":")[-1] for state in CommonFlow.__all_states__}
    assert expected.issubset(state_names)


def _mock_query() -> MagicMock:
    message = MagicMock()
    message.answer = AsyncMock()
    callback = MagicMock(spec=CallbackQuery, message=message, bot=MagicMock())
    callback.answer = AsyncMock()
    return callback


def _mock_state(data: dict | None = None) -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(return_value=dict(data or {}))
    state.set_data = AsyncMock()
    state.set_state = AsyncMock()
    return state


def _mock_session(*rows: list) -> MagicMock:
    session = MagicMock()
    results = []
    for row in rows:
        result = MagicMock()
        result.scalars.return_value.all.return_value = row
        results.append(result)
    session.execute = AsyncMock(side_effect=results)
    session.flush = AsyncMock()
    return session


async def test_choose_region_sends_district_keyboard() -> None:
    from handlers.search import choose_region
    from states.search import SearchFlow

    region = SimpleNamespace(id=1, name_uz="Toshkent", name_ru="Toshkent")
    district = SimpleNamespace(id=7, name_uz="Yunusobod", name_ru="Yunusobod")
    callback = _mock_query()
    state = _mock_state({"sort": "new"})
    session = _mock_session([region], [district])
    i18n = make_i18n(settings.locales_dir, "uz")

    await choose_region(callback, RegionCB(id=1), state, session, i18n)

    callback.answer.assert_awaited_once()
    state.set_state.assert_awaited_once_with(SearchFlow.district)
    data = state.set_data.await_args.args[0]
    assert data["region_id"] == 1
    assert data["region_name"] == "Toshkent"
    markup = callback.message.answer.await_args.kwargs["reply_markup"]
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert "ds:7" in callbacks


async def test_back_from_district_returns_to_region_selection() -> None:
    from handlers.search import back_to_search_regions
    from states.search import SearchFlow

    region = SimpleNamespace(id=1, name_uz="Toshkent", name_ru="Toshkent")
    callback = _mock_query()
    state = _mock_state()
    session = _mock_session([region])
    i18n = make_i18n(settings.locales_dir, "uz")

    await back_to_search_regions(callback, state, session, i18n)

    state.set_state.assert_awaited_once_with(SearchFlow.region)
    markup = callback.message.answer.await_args.kwargs["reply_markup"]
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
    assert "rg:1" in callbacks


async def test_choose_renovation_sends_keyboard() -> None:
    from handlers.search import choose_renovation

    callback = _mock_query()
    i18n = make_i18n(settings.locales_dir, "uz")

    await choose_renovation(callback, i18n)

    markup = callback.message.answer.await_args.kwargs["reply_markup"]
    assert markup.inline_keyboard


async def test_numeric_filter_handler_matches_any_numeric_state() -> None:
    from handlers.search import router as search_router
    from states.search import SearchFlow

    handler = next(
        item for item in search_router.message.handlers if "save_numeric_filter" in str(item.callback)
    )
    assert len(handler.filters) == 1
    state_filter = handler.filters[0].callback
    message = Message(
        message_id=1,
        date=0,
        chat=Chat(id=1, type="private"),
        text="3000000",
    )

    for state in (SearchFlow.rooms, SearchFlow.floor, SearchFlow.guests):
        assert await state_filter(message, raw_state=state.state)
    for state in (
        SearchFlow.min_price,
        SearchFlow.max_price,
        SearchFlow.min_area,
        SearchFlow.max_area,
        SearchFlow.results,
    ):
        assert not await state_filter(message, raw_state=state.state)


async def test_save_numeric_filter_restores_results_state() -> None:
    from handlers.search import save_numeric_filter
    from states.search import SearchFlow

    message = MagicMock()
    message.text = "3"
    message.answer = AsyncMock()
    state = _mock_state({"sort": "new"})
    state.get_state = AsyncMock(return_value=SearchFlow.rooms.state)
    i18n = make_i18n(settings.locales_dir, "uz")

    await save_numeric_filter(message, state, i18n)

    data = state.set_data.await_args.args[0]
    assert data["rooms"] == [3]
    state.set_state.assert_awaited_once_with(SearchFlow.results)


def test_filter_menu_has_no_price_or_area_buttons() -> None:
    from keyboards.inline import filter_menu_kb

    i18n = make_i18n(settings.locales_dir, "uz")
    markup = filter_menu_kb(i18n)
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]

    assert any(item.startswith("fl:rooms") for item in callbacks)
    for prefix in ("fl:min_price", "fl:max_price", "fl:min_area", "fl:max_area"):
        assert not any(item.startswith(prefix) for item in callbacks)


async def test_finish_location_shows_results_without_filter_menu() -> None:
    from handlers.search import finish_location
    from states.search import SearchFlow

    callback = _mock_query()
    state = _mock_state({"listing_type": "SALE", "property_type_id": 2, "region_id": 1})
    session = _mock_session([])
    i18n = make_i18n(settings.locales_dir, "uz")

    await finish_location(callback, state, session, i18n, user=None)

    callback.answer.assert_awaited_once()
    state.set_state.assert_awaited_once_with(SearchFlow.results)
    texts = [call.args[0] for call in callback.message.answer.await_args_list]
    assert callback.message.answer.await_count >= 1
    assert i18n.t("search.filters_title") not in texts
