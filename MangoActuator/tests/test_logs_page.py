from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.enums.gui_enum import TipsTypeEnum
from src.settings import settings
from src.tk_pages.pages.logs import LogsPage, _content_parts, _level_name, _tail_lines, parse_local_log


def test_tail_lines_only_returns_requested_recent_content(tmp_path: Path):
    log_file = tmp_path / "info.log"
    log_file.write_text("\n".join(f"line-{index}" for index in range(20)), encoding="utf-8")

    assert _tail_lines(log_file, 3) == ["line-17", "line-18", "line-19"]


def test_local_log_is_structured_for_display():
    entry = parse_local_log(
        'ERROR   [2026-09-01 16:12:40,157][__init__.py:58] '
        '[元素定位失败] 未找到元素: get_by_role("button")'
    )

    assert entry is not None
    assert entry.timestamp == "09-01 16:12:40"
    assert entry.level == "error"
    assert entry.source == "元素定位失败"
    assert entry.message.startswith("未找到元素")


def test_realtime_log_extracts_source_and_level():
    assert _content_parts("UI-开始执行元素或操作：提交") == ("UI", "开始执行元素或操作：提交")
    assert _level_name(TipsTypeEnum.WARNING, "连接重试") == "warning"
    assert _level_name(None, "执行完成") == "success"
    assert _level_name(None, "元素执行失败") == "error"


def test_runtime_debug_switch_updates_runtime_and_server():
    original_debug = settings.IS_DEBUG
    status = SimpleNamespace(value="", set_status=lambda value: setattr(status, "value", value))
    page = SimpleNamespace(
        debug_var=SimpleNamespace(get=lambda: not original_debug),
        app=status,
    )
    try:
        with (
            patch("src.tk_pages.pages.logs.log.set_debug") as set_debug,
            patch("src.tk_pages.pages.logs.socket_conn.sync_send") as sync_send,
            patch("src.tk_pages.pages.logs.SetConfig.get_username", return_value="tester"),
        ):
            LogsPage._set_debug(page)

        assert settings.IS_DEBUG is (not original_debug)
        set_debug.assert_called_once_with(not original_debug)
        assert sync_send.call_args.kwargs["func_args"].debug is (not original_debug)
        assert status.value == ("调试日志已开启" if settings.IS_DEBUG else "调试日志已关闭")
    finally:
        settings.IS_DEBUG = original_debug
