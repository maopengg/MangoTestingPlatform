import asyncio
import ast
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

import desktop_main
from src.enums.tools_enum import CacheKeyEnum
from src.services.runtime import RuntimeInstanceAlreadyRunning, RuntimeInstanceLock
from src.tk_pages.application import TkActuatorApplication
from src.tk_pages.contracts import HOME_VISIBLE_FIELDS, LOG_VISIBLE_FIELDS, VISIBLE_CONFIG_KEYS
from src.tk_pages.runtime import AsyncRuntimeBridge
from src.tk_pages.pages.config import WebPage
from src.tools import ProjectDir


ACTUATOR_ROOT = Path(__file__).resolve().parents[1]


class TkPagesContractTests(TestCase):
    def test_root_keeps_only_active_entries_and_readme(self):
        visible_files = {
            path.name
            for path in ACTUATOR_ROOT.iterdir()
            if path.is_file() and not path.name.startswith(".")
        }
        self.assertEqual(visible_files, {"README.md", "desktop_main.py", "headless_main.py"})

    def test_actuator_source_does_not_import_legacy_ui_toolkits(self):
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ACTUATOR_ROOT / "src").rglob("*.py")
        ).lower()
        self.assertNotIn("pyside6", source)
        self.assertNotIn("mangoui", source)
        self.assertNotIn("qasync", source)

    def test_visible_config_keys_are_backed_by_cache_keys(self):
        cache_keys = {item.value for item in CacheKeyEnum}
        visible_keys = {key for keys in VISIBLE_CONFIG_KEYS.values() for key in keys}
        self.assertTrue(visible_keys.issubset(cache_keys))

    def test_home_contract_covers_execution_and_connection_information(self):
        self.assertTrue({
            "connection_status", "host", "ws", "task_name", "task_type", "task_id",
            "current_action", "started_at", "elapsed", "progress", "recent_result",
        }.issubset(HOME_VISIBLE_FIELDS))
        self.assertIn("logs", LOG_VISIBLE_FIELDS)
        self.assertTrue({
            "level_filter", "display_limit", "keyword_search", "auto_scroll",
        }.issubset(LOG_VISIBLE_FIELDS))

    def test_monitor_navigation_separates_overview_and_logs(self):
        application = (ACTUATOR_ROOT / "src" / "tk_pages" / "application.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('(\"home\", \"运行概览\", HomePage)', application)
        self.assertIn('(\"logs\", \"实时日志\", LogsPage)', application)

    def test_user_profile_uses_account_entry_instead_of_configuration_menu(self):
        application = (ACTUATOR_ROOT / "src" / "tk_pages" / "application.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('(\"user\", \"用户信息\", UserPage)', application)
        self.assertIn('self.pages[\"user\"] = user_page', application)
        self.assertIn('command=lambda: self.show_page(\"user\")', application)

        home_button = Mock()
        account_button = Mock()
        user_page = Mock(title="用户信息")
        app = SimpleNamespace(
            pages={"user": user_page},
            nav_buttons={"home": home_button},
            account_button=account_button,
            page_title_var=Mock(),
        )

        TkActuatorApplication.show_page(app, "user")

        home_button.set_variant.assert_called_once_with("navigation")
        account_button.set_variant.assert_called_once_with("account_selected")
        app.page_title_var.set.assert_called_once_with("用户信息")
        user_page.tkraise.assert_called_once_with()
        user_page.on_show.assert_called_once_with()

    def test_home_directory_actions_leave_room_for_full_titles(self):
        home = (ACTUATOR_ROOT / "src" / "tk_pages" / "pages" / "home.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("minsize=56", home)
        self.assertGreaterEqual(home.count('width=4, variant="directory_link"'), 2)

    def test_default_entry_uses_flet_application(self):
        entry = (ACTUATOR_ROOT / "desktop_main.py").read_text(encoding="utf-8")
        self.assertIn("run_flet_application", entry)
        tree = ast.parse(entry)
        imported_modules = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules.update(
            str(node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertTrue({"PySide6", "mangoui", "qasync"}.isdisjoint(imported_modules))

    def test_main_window_uses_compact_default_bounds(self):
        application = (ACTUATOR_ROOT / "src" / "tk_pages" / "application.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("min(1120, max(980", application)
        self.assertIn("min(720, max(620", application)

    def test_web_settings_are_persisted_immediately(self):
        status = SimpleNamespace(value="", set=lambda value: setattr(status, "value", value))
        app = SimpleNamespace(value="", set_status=lambda value: setattr(app, "value", value))
        page = SimpleNamespace(auto_save_var=status, app=app)
        setter = Mock()

        WebPage._persist_setting(page, setter, False, "无头模式")

        setter.assert_called_once_with(False)
        self.assertEqual(status.value, "已自动保存：无头模式")
        self.assertEqual(app.value, "已自动保存：无头模式")

    def test_default_desktop_manifests_do_not_install_qt(self):
        requirements = "\n".join(
            (ACTUATOR_ROOT / "requirements" / name).read_text(encoding="utf-8").lower()
            for name in ("desktop.txt", "desktop-local.txt")
        )
        self.assertNotIn("mangoui", requirements)
        self.assertNotIn("pyside", requirements)
        self.assertNotIn("qasync", requirements)
        self.assertIn("pystray", requirements)

    def test_ios_dependencies_are_not_part_of_desktop_base(self):
        desktop_requirements = (ACTUATOR_ROOT / "requirements" / "desktop.txt").read_text(
            encoding="utf-8"
        ).lower()
        ios_requirements = (ACTUATOR_ROOT / "requirements" / "ios.txt").read_text(
            encoding="utf-8"
        ).lower()
        self.assertNotIn("appium-python-client", desktop_requirements)
        self.assertNotIn("selenium", desktop_requirements)
        self.assertIn("appium-python-client", ios_requirements)

    def test_legacy_ui_assets_are_removed(self):
        self.assertFalse((ACTUATOR_ROOT / "src" / "pages").exists())
        self.assertFalse((ACTUATOR_ROOT / "legacy").exists())
        self.assertFalse((ACTUATOR_ROOT / "requirements" / "legacy-qt.txt").exists())
        self.assertEqual(list((ACTUATOR_ROOT / "local_packages").glob("mangoui-*.whl")), [])

    def test_frozen_macos_runtime_uses_application_support(self):
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "platform", "darwin"),
            patch.object(sys, "executable", "/Applications/MangoActuator.app/Contents/MacOS/MangoActuator"),
            patch("src.tools.Path.home", return_value=Path("/Users/tester")),
        ):
            self.assertEqual(
                ProjectDir.init_project_path(),
                "/Users/tester/Library/Application Support/MangoActuator",
            )

    def test_duplicate_desktop_instance_is_reported_without_traceback(self):
        error = RuntimeInstanceAlreadyRunning("已有实例（PID 123）")
        with (
            patch("src.flet_pages.application.run_flet_application", side_effect=error),
            patch.object(desktop_main, "_show_duplicate_instance_warning") as show_warning,
            patch("src.tools.log_collector.log.warning") as log_warning,
        ):
            desktop_main.run_desktop()
        show_warning.assert_called_once_with(str(error))
        log_warning.assert_called_once_with(str(error))


class RuntimeInstanceLockTests(TestCase):
    def test_lock_conflict_includes_owner_pid_and_resolution(self):
        lock_file = Mock()
        lock_file.read.return_value = "13187"
        instance_lock = RuntimeInstanceLock("/tmp/mango-runtime/cache/actuator.lock")
        with (
            patch.object(Path, "open", return_value=lock_file),
            patch.object(Path, "mkdir"),
            patch.object(instance_lock, "_lock_file", side_effect=BlockingIOError),
            self.assertRaises(RuntimeInstanceAlreadyRunning) as raised,
        ):
            instance_lock.acquire()
        self.assertIn("PID 13187", str(raised.exception))
        self.assertIn("MANGO_ACTUATOR_RUNTIME_DIR", str(raised.exception))
        lock_file.close.assert_called_once()


class AsyncRuntimeBridgeTests(TestCase):
    def test_coroutine_result_is_marshaled_to_callback_queue(self):
        bridge = AsyncRuntimeBridge()
        bridge.start()
        try:
            received = []

            async def value():
                await asyncio.sleep(0)
                return 42

            bridge.submit(value(), received.append).result(timeout=3)
            deadline = time.time() + 3
            callbacks = []
            while time.time() < deadline and not callbacks:
                callbacks = bridge.drain_callbacks()
                time.sleep(0.01)
            for callback, args in callbacks:
                callback(*args)
            self.assertEqual(received, [42])
        finally:
            if bridge.loop and bridge.loop.is_running():
                bridge.loop.call_soon_threadsafe(bridge.loop.stop)
            if bridge._thread:
                bridge._thread.join(timeout=3)
