import asyncio
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from src.flet_pages.application import FletActuatorApplication
from src.flet_pages.config import config_view
from src.flet_pages.select import CompactSelect


class FletPagesTests(TestCase):
    def test_compact_select_preserves_option_key_in_change_event(self):
        changed = Mock()
        select = CompactSelect(options=[("1", "一个"), ("2", "两个")], value="1", on_change=changed)
        select.update = Mock()
        event = SimpleNamespace(target="item", page=Mock())
        select.menu.items[1].on_click(event)
        self.assertEqual(select.value, "2")
        self.assertEqual(select.selected_text.value, "两个")
        self.assertIs(changed.call_args.args[0].control, select)
        self.assertEqual(changed.call_args.args[0].data, "2")
        self.assertTrue(all(item.height == 32 for item in select.menu.items))
        select.menu.items[1].on_click(event)
        changed.assert_called_once()

    def make_app(self):
        page = Mock(window=SimpleNamespace(center=Mock()), controls=[])
        with patch("src.flet_pages.application.AsyncRuntimeBridge"), patch(
            "src.flet_pages.application.SetConfig.get_remembered_login", return_value=("", "", False)
        ):
            return FletActuatorApplication(page)

    def test_all_configuration_pages_construct_with_saved_settings(self):
        app = self.make_app()
        for key in ("web", "android", "ios", "pc", "pytest", "settings"):
            with self.subTest(page=key):
                self.assertIsNotNone(config_view(app, key))
        self.assertIsNotNone(app.home())
        self.assertIsNotNone(app.log_view())

    def test_login_is_prepared_and_centered_before_window_is_shown(self):
        page = Mock(window=SimpleNamespace(center=Mock(), visible=False), controls=[])
        visible_at_update = []
        page.update.side_effect = lambda: visible_at_update.append(page.window.visible)
        with patch("src.flet_pages.application.AsyncRuntimeBridge"), patch(
            "src.flet_pages.application.SetConfig.get_remembered_login", return_value=("", "", False)
        ), patch("src.flet_pages.application.SetConfig.get_proxy_url", return_value=None):
            FletActuatorApplication(page)
        self.assertEqual(visible_at_update, [False, True])
        self.assertEqual((page.window.width, page.window.height), (360, 470))
        page.window.center.assert_called_once_with()

    def test_failed_login_restores_button_for_retry(self):
        app = self.make_app()
        app.username.value, app.password.value = "tester", "example-password"
        def timeout(coroutine):
            coroutine.close()
            raise TimeoutError("连接超时")
        app.bridge.submit.side_effect = timeout
        with patch.object(app, "endpoint"):
            asyncio.run(app.login(None))
        self.assertFalse(app.login_button.disabled)
        self.assertIn("超时", app.login_status.value)

    def test_main_window_expands_after_login(self):
        app = self.make_app()
        self.assertTrue(app.page.window.resizable)
        app.page.window.center.assert_called_once_with()
        app.page.window.center.reset_mock()
        centered_sizes = []
        app.page.window.center.side_effect = lambda: centered_sizes.append((
            app.page.window.width, app.page.window.height,
        ))
        with patch.object(app.tray, "start"), patch.object(app, "show_page"), patch(
            "src.flet_pages.application.process", new=Mock(return_value=Mock()),
        ):
            app.show_main()

        self.assertEqual((app.page.window.width, app.page.window.height), (1120, 760))
        self.assertEqual((app.page.window.min_width, app.page.window.min_height), (960, 640))
        self.assertTrue(app.page.window.resizable)
        self.assertEqual(centered_sizes, [(1120, 760)])

    def test_close_with_tray_hides_window_without_stopping_runtime(self):
        app = self.make_app()
        app.tray.icon = Mock()
        app.window_event(SimpleNamespace(data="close"))
        self.assertFalse(app.page.window.visible)
        app.bridge.stop.assert_not_called()

    def test_logs_filter_and_bound_rendered_rows(self):
        app = self.make_app()
        app.log_view()
        app.logs.extend(("12:00:00", "error", f"失败 {i}") for i in range(600))
        app.level.value = "error"
        app.limit.value = "200"
        app.keyword.value = "失败"
        app.render_logs()
        self.assertEqual(len(app.log_list.controls), 200)

    def test_overview_keeps_zero_elapsed_and_updates_recent_result(self):
        app = self.make_app()
        with patch("src.flet_pages.application.ExecutionActivity.snapshot", return_value={
            "active": [{"task_name": "示例任务", "elapsed_seconds": 0,
                        "progress_current": 1, "progress_total": 2}], "recent": [],
        }):
            app.home()
        self.assertEqual(app.task_fields["elapsed_seconds"].controls[1].value, "0")
        self.assertEqual(app.task_fields["task_name"].controls[1].value, "示例任务")
        self.assertEqual(app.progress.value, 0.5)
        with patch("src.flet_pages.application.ExecutionActivity.snapshot", return_value={
            "active": [], "recent": [{"status": "failed", "error_message": "断言未通过"}],
        }):
            app.refresh_activity()
        self.assertTrue(app.recent_result.visible)
        self.assertEqual(app.recent_result.value, "最近结果：失败 · 断言未通过")
