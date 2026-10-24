import inspect
from types import SimpleNamespace
from unittest.mock import patch

from src.settings import settings
from src.tk_pages.pages.home import HomePage


def test_runtime_open_switch_is_below_connection_detail_rows():
    source = inspect.getsource(HomePage._build_connection)
    assert "controls.grid(row=len(rows) + 1" in source


def test_runtime_open_switch_updates_mode_and_server():
    original_open = settings.IS_OPEN
    mode = SimpleNamespace(value="", set=lambda value: setattr(mode, "value", value))
    page = SimpleNamespace(
        open_var=SimpleNamespace(get=lambda: not original_open),
        connection_vars={"mode": mode},
    )

    def apply_open(value):
        settings.IS_OPEN = bool(value)
        return settings.IS_OPEN

    try:
        with (
            patch("src.tk_pages.pages.home.SetConfig.set_open_status", side_effect=apply_open),
            patch("src.tk_pages.pages.home.SetConfig.get_username", return_value="tester"),
            patch("src.tk_pages.pages.home.socket_conn.sync_send") as sync_send,
        ):
            HomePage._set_open(page)

        assert settings.IS_OPEN is (not original_open)
        assert mode.value == ("开放领取" if settings.IS_OPEN else "仅定向任务")
        assert sync_send.call_args.kwargs["func_args"].is_open is (not original_open)
    finally:
        settings.IS_OPEN = original_open
