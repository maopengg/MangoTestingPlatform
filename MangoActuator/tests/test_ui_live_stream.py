import asyncio
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, mock

from src.consumer import SocketConsumer
from src.consumer.ui import UI
from mangotools.contracts import SocketCommandContract
from src.services.ui.live_stream.capture import LatestFrameBuffer
from src.services.ui.live_stream.capture import RuntimeFrameCapture
from src.services.ui.live_stream.client import UiLiveStreamClient
from src.services.ui.live_stream.control import RemoteControlExecutor
from src.services.ui.live_stream.manager import UiLiveStreamManager
from src.services.ui.live_stream.runtime_registry import UiRuntimeRegistry
from src.services.ui.live_workspace import UiLiveWorkspaceManager
from src.services.ui.test_page_steps import TestPageSteps


class UiLiveStreamRuntimeTest(IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        UiRuntimeRegistry._states.clear()
        UiRuntimeRegistry._page_states.clear()
        UiLiveWorkspaceManager._states.clear()
        UiLiveWorkspaceManager._start_locks.clear()
        UI._slot_services.clear()
        if UiLiveWorkspaceManager._watchdog_task:
            UiLiveWorkspaceManager._watchdog_task.cancel()
            await asyncio.gather(UiLiveWorkspaceManager._watchdog_task, return_exceptions=True)
            UiLiveWorkspaceManager._watchdog_task = None
        for task in tuple(SocketConsumer.background_tasks):
            task.cancel()
        await asyncio.gather(*SocketConsumer.background_tasks, return_exceptions=True)
        SocketConsumer.background_tasks.clear()
        for task in tuple(UiLiveStreamManager._tasks.values()):
            task.cancel()
        await asyncio.gather(*UiLiveStreamManager._tasks.values(), return_exceptions=True)
        UiLiveStreamManager._tasks.clear()
        UiLiveStreamManager._clients.clear()
        UiLiveStreamManager._commands.clear()
        UiLiveStreamManager._starting.clear()
        UiLiveStreamManager._cancelled.clear()

    async def test_aliases_share_pause_and_operation_state(self):
        page = SimpleNamespace(is_closed=lambda: False)
        base_data = SimpleNamespace(page=page)
        state = await UiRuntimeRegistry.register("ui_case", 100, base_data)
        await UiRuntimeRegistry.register_alias("ui_case", 200, state)
        self.assertIs(await UiRuntimeRegistry.wait_for("ui_case", 200), state)

        await UiRuntimeRegistry.pause_automation(state)
        entered = asyncio.Event()

        async def guarded_operation():
            async with UiRuntimeRegistry.operation_guard(page):
                entered.set()

        task = asyncio.create_task(guarded_operation())
        await asyncio.sleep(0)
        self.assertFalse(entered.is_set())
        await UiRuntimeRegistry.resume_automation(state)
        await asyncio.wait_for(task, timeout=1)
        self.assertTrue(entered.is_set())

    async def test_latest_frame_buffer_discards_old_frame(self):
        buffer = LatestFrameBuffer()
        buffer.offer(b"old")
        buffer.offer(b"new")
        self.assertEqual(await buffer.get(), b"new")

    async def test_ios_runtime_can_be_registered_without_web_page(self):
        ios = SimpleNamespace(session_id="ios-session")
        base_data = SimpleNamespace(page=None, ios=ios, bundle_id="com.example.demo")

        state = await UiRuntimeRegistry.register("ui_case", 301, base_data)

        self.assertIs(await UiRuntimeRegistry.wait_for("ui_case", 301), state)
        self.assertEqual(state.display_url, "ios://com.example.demo")

    async def test_ios_capture_publishes_appium_screenshot(self):
        ios = SimpleNamespace(get_screenshot_as_png=mock.Mock(return_value=b"png-frame"))
        state = SimpleNamespace(ios=ios, page=None)
        buffer = LatestFrameBuffer()
        capture = RuntimeFrameCapture(state, {"fps": 1}, buffer)

        task = asyncio.create_task(capture.run())
        self.assertEqual(await asyncio.wait_for(buffer.get(), timeout=1), b"png-frame")
        capture.stop()
        await asyncio.wait_for(task, timeout=2)

    async def test_ios_live_control_maps_click_scroll_and_text(self):
        class OperationLock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        active_element = SimpleNamespace(send_keys=mock.Mock())
        ios = SimpleNamespace(
            get_window_size=mock.Mock(return_value={"width": 390, "height": 844}),
            execute_script=mock.Mock(),
            switch_to=SimpleNamespace(active_element=active_element),
        )
        state = SimpleNamespace(
            ios=ios,
            page=None,
            operation_lock=OperationLock(),
            base_data=SimpleNamespace(bundle_id="com.example.demo"),
            display_url="ios://com.example.demo",
        )
        executor = RemoteControlExecutor(state)

        await executor.execute({"event_type": "mouse_click", "x": 0.5, "y": 0.25})
        await executor.execute({"event_type": "mouse_wheel", "delta_y": 100})
        await executor.execute({"event_type": "text_input", "text": "中文输入"})

        self.assertEqual(
            ios.execute_script.call_args_list,
            [
                mock.call("mobile: tap", {"x": 195.0, "y": 211.0}),
                mock.call("mobile: swipe", {"direction": "up"}),
            ],
        )
        active_element.send_keys.assert_called_once_with("中文输入")

    async def test_mouse_wheel_moves_to_live_pointer_before_scrolling(self):
        class OperationLock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        mouse = SimpleNamespace(move=mock.AsyncMock(), wheel=mock.AsyncMock())
        page = SimpleNamespace(
            is_closed=lambda: False,
            viewport_size={"width": 1440, "height": 900},
            mouse=mouse,
        )
        executor = RemoteControlExecutor(SimpleNamespace(page=page, operation_lock=OperationLock()))

        await executor.execute({
            "event_type": "mouse_wheel",
            "x": 0.25,
            "y": 0.75,
            "delta_x": 0,
            "delta_y": 160,
        })

        mouse.move.assert_awaited_once_with(360, 675)
        mouse.wheel.assert_awaited_once_with(0.0, 160.0)

    async def test_record_action_is_delegated_to_shared_recorder(self):
        class OperationLock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        page = SimpleNamespace(is_closed=lambda: False)
        executor = RemoteControlExecutor(SimpleNamespace(page=page, operation_lock=OperationLock()))
        executor.recorder.execute = mock.AsyncMock(return_value={
            "action": "click",
            "element": {"text": "提交"},
        })

        result = await executor.execute({"event_type": "record_action", "action": "click"})

        executor.recorder.execute.assert_awaited_once_with(
            page,
            {"event_type": "record_action", "action": "click"},
        )
        self.assertEqual(result["recorded_action"]["element"]["text"], "提交")

    async def test_live_text_input_inserts_complete_chinese_text(self):
        class OperationLock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        keyboard = SimpleNamespace(insert_text=mock.AsyncMock())
        page = SimpleNamespace(is_closed=lambda: False, keyboard=keyboard)
        executor = RemoteControlExecutor(
            SimpleNamespace(page=page, operation_lock=OperationLock())
        )

        await executor.execute({"event_type": "text_input", "text": "生成一份销售订单"})

        keyboard.insert_text.assert_awaited_once_with("生成一份销售订单")

    async def test_record_poll_returns_passive_actions(self):
        class OperationLock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

        page = SimpleNamespace(is_closed=lambda: False)
        executor = RemoteControlExecutor(SimpleNamespace(page=page, operation_lock=OperationLock()))
        executor.recorder.poll_passive_events = mock.AsyncMock(return_value=[{"action": "navigation"}])

        result = await executor.execute({"event_type": "record_poll"})

        self.assertEqual(result, {"passive_actions": [{"action": "navigation"}]})

    async def test_scanned_locator_check_returns_every_locator_group(self):
        page = SimpleNamespace(
            url="https://example.test/page",
            title=mock.AsyncMock(return_value="测试页面"),
            viewport_size={"width": 1440, "height": 900},
        )
        executor = RemoteControlExecutor(SimpleNamespace())
        executor.inspector.validate = mock.AsyncMock(return_value={
            "status": True,
            "selected_group": 2,
            "selected": {
                "group": 2,
                "exp": 2,
                "loc": 'get_by_role("button", name="提交")',
                "sub": None,
                "status": "risk",
                "count": 2,
                "visible": True,
                "enabled": True,
                "editable": False,
                "element_text": "提交",
                "bounding_box": {"x": 10, "y": 20, "width": 80, "height": 30},
            },
            "locator_groups": [
                {"group": 1, "status": "invalid", "count": 0},
                {"group": 2, "status": "risk", "count": 2, "highlighted": True},
                {"group": 3, "status": "invalid", "count": 1},
                {"group": 4, "status": "valid", "count": 1},
                {"group": 5, "status": "invalid", "count": 0},
            ],
            "reject_reasons": ["第一组匹配 0"],
            "baseline_snapshot": {"tag": "button"},
            "duration_ms": 12,
        })

        payload = await executor._check_locator(page, {
            "row_key": "scan-row-1",
            "name": "提交",
            "locators": [
                {"exp": 2, "loc": 'get_by_role("button", name="不存在")'},
                {"exp": 2, "loc": 'get_by_role("button", name="提交")'},
                {"exp": 9, "loc": ".hidden-submit"},
                {"exp": 9, "loc": "button[data-testid=submit]"},
                {"exp": 0, "loc": "//button[@name='submit']"},
            ],
        })

        result = payload["scan_check_result"]
        self.assertEqual(result["status"], 1)
        self.assertEqual(result["selected_group"], 2)
        self.assertEqual(
            [item["status"] for item in result["locator_groups"]],
            ["invalid", "risk", "invalid", "valid", "invalid"],
        )
        self.assertEqual(
            [item["count"] for item in result["locator_groups"]],
            [0, 2, 1, 1, 0],
        )
        self.assertTrue(result["locator_groups"][1]["highlighted"])
        validated_locators = executor.inspector.validate.await_args.args[1]
        self.assertEqual(len(validated_locators), 5)

    async def test_control_timeout_releases_inputs_and_resumes_automation(self):
        page = SimpleNamespace(is_closed=lambda: False)
        state = await UiRuntimeRegistry.register("ui_case", 100, SimpleNamespace(page=page))
        await UiRuntimeRegistry.pause_automation(state)
        client = UiLiveStreamClient(state, {"stream_id": "stream-1"})
        client.control.release_all = mock.AsyncMock()

        await client._control_lease_timeout(0)

        client.control.release_all.assert_awaited_once()
        self.assertTrue(state.automation_allowed.is_set())

    async def test_slow_control_returns_timeout_ack(self):
        state = SimpleNamespace(page=SimpleNamespace(is_closed=lambda: False))
        client = UiLiveStreamClient(state, {"stream_id": "stream-1"})
        client.CONTROL_EVENT_TIMEOUT_SECONDS = 0.01

        async def slow_control(_event):
            await asyncio.sleep(1)

        client.control.execute = mock.AsyncMock(side_effect=slow_control)
        websocket = SimpleNamespace(send=mock.AsyncMock())

        await client._execute_control_event(
            websocket,
            {"event_type": "mouse_click", "sequence": 1},
        )

        payload = websocket.send.await_args.args[0]
        self.assertIn('"success": false', payload)
        self.assertIn("实时控制执行超时", payload)

    async def test_live_stream_serializes_concurrent_websocket_writes(self):
        state = SimpleNamespace(page=SimpleNamespace(is_closed=lambda: False))
        client = UiLiveStreamClient(state, {"stream_id": "stream-serialized-send"})

        class WebSocket:
            def __init__(self):
                self.sending = False
                self.payloads = []

            async def send(self, payload):
                if self.sending:
                    raise AssertionError("concurrent websocket send")
                self.sending = True
                await asyncio.sleep(0)
                self.payloads.append(payload)
                self.sending = False

        websocket = WebSocket()
        await asyncio.gather(
            client._send(websocket, b"frame"),
            client._send(websocket, '{"type":"control_ack"}'),
        )

        self.assertEqual(websocket.payloads, [b"frame", '{"type":"control_ack"}'])

    async def test_completed_case_stream_sends_normal_end_status_before_stop(self):
        state = SimpleNamespace(page=SimpleNamespace(is_closed=lambda: False))
        client = UiLiveStreamClient(state, {"stream_id": "stream-case-completed"})
        websocket = SimpleNamespace(send=mock.AsyncMock())
        client._websocket = websocket

        await client.stop(reason="execution_completed")

        payload = websocket.send.await_args.args[0]
        self.assertIn('"status": "completed"', payload)
        self.assertIn('"reason": "execution_completed"', payload)
        self.assertFalse(client.running)

    async def test_live_stream_command_bypasses_serial_business_queue(self):
        started = asyncio.Event()

        async def immediate(_data):
            started.set()

        command = SocketCommandContract(func_name="u_live_stream_start", func_args={"stream_id": "stream-1"})
        with mock.patch.object(SocketConsumer, "u_live_stream_start", side_effect=immediate):
            await SocketConsumer.add_task(command)
            await asyncio.wait_for(started.wait(), timeout=1)

        self.assertTrue(SocketConsumer.queue.empty())

    async def test_live_workspace_ready_status_targets_requesting_web_user(self):
        command = {
            "workspace_id": "workspace-1",
            "runtime_data": {"send_user": "maopeng"},
        }
        with mock.patch(
            "src.services.ui.live_workspace.socket_conn.async_send",
            new_callable=mock.AsyncMock,
        ) as async_send:
            await UiLiveWorkspaceManager._notify_status(command, "ready")

        async_send.assert_awaited_once()
        kwargs = async_send.await_args.kwargs
        self.assertEqual(kwargs["user"], "maopeng")
        self.assertEqual(kwargs["func_name"], "u_live_workspace_status")
        self.assertTrue(kwargs["reliable"])
        self.assertEqual(
            kwargs["func_args"],
            {
                "workspace_id": "workspace-1",
                "status": "ready",
                "message": "",
                "slot_id": "",
                "idle_timeout_seconds": 300,
                "idle_deadline": None,
            },
        )

    async def test_live_workspace_reuses_context_when_auth_cache_is_unchanged(self):
        auth_cache = {"cookies": [{"name": "session", "value": "same"}]}
        runtime_data = SimpleNamespace(
            name="授权页面",
            ui_auth_cache=auth_cache,
            workspace_id=None,
            slot_id=None,
        )
        existing = SimpleNamespace(
            base_data=SimpleNamespace(page=object(), ios=None),
            runtime_data=runtime_data,
            auth_cache_signature=UiLiveWorkspaceManager._auth_cache_signature(auth_cache),
        )
        command = {
            "workspace_id": "workspace-auth",
            "slot_id": "slot-auth",
            "workspace_type": "page_step_workspace",
            "runtime_data": {"ui_auth_cache": auth_cache},
        }

        with (
            mock.patch(
                "src.services.ui.live_workspace.DebugPageStepsModel",
                return_value=runtime_data,
            ),
            mock.patch.object(UiLiveWorkspaceManager, "_ensure_watchdog", new_callable=mock.AsyncMock),
            mock.patch.object(UiLiveWorkspaceManager, "_ensure_slot_capacity", new_callable=mock.AsyncMock),
            mock.patch.object(UiLiveWorkspaceManager, "get", new_callable=mock.AsyncMock, return_value=existing),
            mock.patch.object(UiLiveWorkspaceManager, "_runtime_available", return_value=True),
            mock.patch.object(UiLiveWorkspaceManager, "touch", new_callable=mock.AsyncMock) as touch,
            mock.patch.object(UiLiveWorkspaceManager, "stop", new_callable=mock.AsyncMock) as stop,
            mock.patch.object(UiRuntimeRegistry, "register", new_callable=mock.AsyncMock),
            mock.patch.object(UiLiveWorkspaceManager, "_notify_status", new_callable=mock.AsyncMock),
        ):
            await UiLiveWorkspaceManager.start(command)

        touch.assert_awaited_once_with("workspace-auth")
        stop.assert_not_awaited()

    async def test_live_workspace_rebuilds_context_when_auth_cache_changes(self):
        old_auth_cache = {"cookies": [{"name": "session", "value": "old"}]}
        new_auth_cache = {"cookies": [{"name": "session", "value": "new"}]}
        old_runtime_data = SimpleNamespace(name="授权页面", ui_auth_cache=old_auth_cache)
        new_runtime_data = SimpleNamespace(
            name="授权页面",
            ui_auth_cache=new_auth_cache,
            workspace_id=None,
            slot_id=None,
            test_env=2,
            type=1,
            send_user="maopeng",
        )
        existing = SimpleNamespace(
            base_data=SimpleNamespace(page=object(), ios=None),
            runtime_data=old_runtime_data,
            auth_cache_signature=UiLiveWorkspaceManager._auth_cache_signature(old_auth_cache),
        )
        new_base_data = SimpleNamespace(page=None, ios=object())
        page_steps = SimpleNamespace(
            driver_init=mock.AsyncMock(),
            page_init=mock.AsyncMock(),
        )
        auth_applier = SimpleNamespace(apply=mock.AsyncMock())
        command = {
            "workspace_id": "workspace-auth",
            "slot_id": "slot-auth",
            "workspace_type": "page_step_workspace",
            "runtime_data": {"ui_auth_cache": new_auth_cache},
        }

        with (
            mock.patch(
                "src.services.ui.live_workspace.DebugPageStepsModel",
                return_value=new_runtime_data,
            ),
            mock.patch.object(UiLiveWorkspaceManager, "_ensure_watchdog", new_callable=mock.AsyncMock),
            mock.patch.object(UiLiveWorkspaceManager, "_ensure_slot_capacity", new_callable=mock.AsyncMock),
            mock.patch.object(UiLiveWorkspaceManager, "get", new_callable=mock.AsyncMock, return_value=existing),
            mock.patch.object(UiLiveWorkspaceManager, "_runtime_available", return_value=True),
            mock.patch.object(
                UiLiveWorkspaceManager,
                "_stop_other_slot_workspace",
                new_callable=mock.AsyncMock,
            ),
            mock.patch.object(UiLiveWorkspaceManager, "stop", new_callable=mock.AsyncMock) as stop,
            mock.patch(
                "src.services.ui.live_workspace.AutomationSessionManager.web_runtime",
                return_value=object(),
            ),
            mock.patch(
                "src.services.ui.live_workspace.AutomationSessionManager.create_base_data",
                return_value=new_base_data,
            ),
            mock.patch("src.services.ui.live_workspace.PageSteps", return_value=page_steps),
            mock.patch(
                "src.services.ui.live_workspace.UiAuthCacheApplier",
                return_value=auth_applier,
            ),
            mock.patch.object(UiRuntimeRegistry, "register", new_callable=mock.AsyncMock),
            mock.patch.object(UiLiveWorkspaceManager, "_notify_status", new_callable=mock.AsyncMock),
        ):
            await UiLiveWorkspaceManager.start(command)

        stop.assert_awaited_once_with("workspace-auth", reason="restart")
        auth_applier.apply.assert_awaited_once()
        state = UiLiveWorkspaceManager._states["workspace-auth"]
        self.assertIs(state.base_data, new_base_data)
        self.assertEqual(
            state.auth_cache_signature,
            UiLiveWorkspaceManager._auth_cache_signature(new_auth_cache),
        )

    async def test_wait_for_live_workspace_does_not_fall_back_before_ready(self):
        page = SimpleNamespace(is_closed=lambda: False)
        state = SimpleNamespace(base_data=SimpleNamespace(page=page))
        wait_task = asyncio.create_task(UiLiveWorkspaceManager.wait_for("workspace-1", timeout=1))
        await asyncio.sleep(0)
        self.assertFalse(wait_task.done())

        UiLiveWorkspaceManager._states["workspace-1"] = state

        self.assertIs(await asyncio.wait_for(wait_task, timeout=1), state)

    async def test_stop_before_runtime_registration_prevents_late_start(self):
        release_wait = asyncio.Event()
        runtime_state = SimpleNamespace(
            execution_type="ui_case",
            execution_id="100",
            page=SimpleNamespace(url="about:blank"),
        )

        async def delayed_wait(*_args, **_kwargs):
            await release_wait.wait()
            return runtime_state

        command = {
            "stream_id": "stream-late",
            "execution_type": "ui_case",
            "execution_id": "100",
        }
        with mock.patch.object(UiRuntimeRegistry, "wait_for", side_effect=delayed_wait):
            start_task = asyncio.create_task(UiLiveStreamManager.start(command))
            await asyncio.sleep(0)
            await UiLiveStreamManager.stop("stream-late")
            release_wait.set()
            await start_task

        self.assertNotIn("stream-late", UiLiveStreamManager._tasks)
        self.assertNotIn("stream-late", UiLiveStreamManager._clients)

    async def test_case_live_start_returns_while_waiting_for_case_runtime(self):
        wait_started = asyncio.Event()
        release_wait = asyncio.Event()
        stream_started = asyncio.Event()
        keep_streaming = asyncio.Event()
        runtime_state = SimpleNamespace(
            execution_type="ui_case",
            execution_id="case-execution-1",
            page=SimpleNamespace(url="about:blank"),
        )

        async def delayed_wait(*_args, **kwargs):
            self.assertIsNone(kwargs["timeout"])
            wait_started.set()
            await release_wait.wait()
            return runtime_state

        async def run_stream():
            stream_started.set()
            await keep_streaming.wait()

        client = SimpleNamespace(run=mock.AsyncMock(side_effect=run_stream), stop=mock.AsyncMock())
        command = {
            "stream_id": "stream-case-waiting",
            "execution_type": "ui_case",
            "execution_id": "case-execution-1",
        }
        with (
            mock.patch.object(UiRuntimeRegistry, "wait_for", side_effect=delayed_wait),
            mock.patch(
                "src.services.ui.live_stream.manager.UiLiveStreamClient",
                return_value=client,
            ),
        ):
            await asyncio.wait_for(UiLiveStreamManager.start(command), timeout=0.1)
            await asyncio.wait_for(wait_started.wait(), timeout=0.1)
            self.assertIn("stream-case-waiting", UiLiveStreamManager._tasks)
            self.assertNotIn("stream-case-waiting", UiLiveStreamManager._clients)

            release_wait.set()
            await asyncio.wait_for(stream_started.wait(), timeout=0.1)
            self.assertIs(UiLiveStreamManager._clients["stream-case-waiting"], client)

            await UiLiveStreamManager.stop("stream-case-waiting")

        client.stop.assert_awaited_once()
        self.assertNotIn("stream-case-waiting", UiLiveStreamManager._tasks)
        self.assertNotIn("stream-case-waiting", UiLiveStreamManager._clients)

    async def test_case_live_wait_can_be_cancelled_before_case_execution(self):
        wait_started = asyncio.Event()

        async def wait_forever(*_args, **_kwargs):
            wait_started.set()
            await asyncio.Event().wait()

        command = {
            "stream_id": "stream-case-cancelled",
            "execution_type": "ui_case",
            "execution_id": "case-execution-2",
        }
        with mock.patch.object(UiRuntimeRegistry, "wait_for", side_effect=wait_forever):
            await UiLiveStreamManager.start(command)
            await asyncio.wait_for(wait_started.wait(), timeout=0.1)
            await UiLiveStreamManager.stop("stream-case-cancelled")

        self.assertNotIn("stream-case-cancelled", UiLiveStreamManager._tasks)
        self.assertNotIn("stream-case-cancelled", UiLiveStreamManager._clients)

    async def test_case_end_cancels_pending_live_wait_by_execution_id(self):
        wait_started = asyncio.Event()

        async def wait_forever(*_args, **_kwargs):
            wait_started.set()
            await asyncio.Event().wait()

        command = {
            "stream_id": "stream-case-ended",
            "execution_type": "ui_case",
            "execution_id": "case-execution-3",
        }
        with mock.patch.object(UiRuntimeRegistry, "wait_for", side_effect=wait_forever):
            await UiLiveStreamManager.start(command)
            await asyncio.wait_for(wait_started.wait(), timeout=0.1)
            self.assertTrue(
                await UiLiveStreamManager.has_execution("ui_case", "case-execution-3")
            )

            await UiLiveStreamManager.stop_execution("ui_case", "case-execution-3")

        self.assertNotIn("stream-case-ended", UiLiveStreamManager._tasks)
        self.assertNotIn("stream-case-ended", UiLiveStreamManager._commands)

    async def test_case_end_passes_normal_completion_reason_to_live_client(self):
        client = SimpleNamespace(stop=mock.AsyncMock())
        UiLiveStreamManager._clients["stream-case-completed"] = client
        UiLiveStreamManager._commands["stream-case-completed"] = {
            "stream_id": "stream-case-completed",
            "execution_type": "ui_case",
            "execution_id": "case-execution-completed",
        }

        await UiLiveStreamManager.stop_execution(
            "ui_case",
            "case-execution-completed",
            reason="execution_completed",
        )

        client.stop.assert_awaited_once_with(reason="execution_completed")

    async def test_workspace_manager_accepts_five_distinct_user_slots(self):
        for index in range(5):
            UiLiveWorkspaceManager._states[f"workspace-{index}"] = SimpleNamespace(
                workspace_id=f"workspace-{index}",
                slot_id=f"slot-{index}",
            )

        await UiLiveWorkspaceManager._ensure_slot_capacity("slot-0")
        with self.assertRaisesRegex(RuntimeError, "5/5"):
            await UiLiveWorkspaceManager._ensure_slot_capacity("slot-6")

    async def test_new_workspace_only_replaces_workspace_from_same_slot(self):
        UiLiveWorkspaceManager._states.update({
            "same-slot-old": SimpleNamespace(slot_id="slot-1"),
            "other-user": SimpleNamespace(slot_id="slot-2"),
        })

        with mock.patch.object(
            UiLiveWorkspaceManager,
            "stop",
            new_callable=mock.AsyncMock,
        ) as stop:
            await UiLiveWorkspaceManager._stop_other_slot_workspace(
                "slot-1",
                "same-slot-new",
            )

        stop.assert_awaited_once_with("same-slot-old", reason="same-slot-replaced")

    async def test_workspace_stop_waits_for_running_element_check(self):
        operation_idle = asyncio.Event()
        state = SimpleNamespace(
            workspace_id="workspace-running",
            workspace_type="element_workspace",
            slot_id="slot-running",
            send_user=None,
            base_data=SimpleNamespace(page=object()),
            running=True,
            operation_idle=operation_idle,
            last_activity_at=0,
        )
        UiLiveWorkspaceManager._states[state.workspace_id] = state

        with (
            mock.patch.object(
                UiLiveStreamManager,
                "stop_execution",
                new_callable=mock.AsyncMock,
            ),
            mock.patch.object(
                UiRuntimeRegistry,
                "unregister",
                new_callable=mock.AsyncMock,
            ),
            mock.patch(
                "src.services.ui.live_workspace.AutomationSessionManager.close_page_context",
                new_callable=mock.AsyncMock,
            ) as close_page_context,
        ):
            stop_task = asyncio.create_task(
                UiLiveWorkspaceManager.stop(state.workspace_id, reason="closed")
            )
            await asyncio.sleep(0)

            self.assertFalse(stop_task.done())
            close_page_context.assert_not_awaited()

            await UiLiveWorkspaceManager.set_running(state.workspace_id, False)
            await asyncio.wait_for(stop_task, timeout=1)

        close_page_context.assert_awaited_once_with(state.base_data, "UI实时工作区")
        self.assertNotIn(state.workspace_id, UiLiveWorkspaceManager._states)

    async def test_idle_workspace_expires_but_running_or_live_workspace_does_not(self):
        UiLiveWorkspaceManager._states.update({
            "idle": SimpleNamespace(
                workspace_id="idle",
                last_activity_at=0,
                running=False,
                live_stream_count=0,
            ),
            "running": SimpleNamespace(
                workspace_id="running",
                last_activity_at=0,
                running=True,
                live_stream_count=0,
            ),
            "live": SimpleNamespace(
                workspace_id="live",
                last_activity_at=0,
                running=False,
                live_stream_count=1,
            ),
        })

        expired = await UiLiveWorkspaceManager.expired_workspace_ids(now=301)

        self.assertEqual(expired, ["idle"])

    async def test_page_step_services_are_isolated_by_user_slot(self):
        UI.parent = SimpleNamespace()

        first = UI._page_step_service("slot-1", 7)
        reopened = UI._page_step_service("slot-1", 7)
        second = UI._page_step_service("slot-2", 7)

        self.assertIs(first, reopened)
        self.assertIsNot(first, second)

    async def test_non_workspace_debug_browser_closes_after_idle_timeout(self):
        service = TestPageSteps(SimpleNamespace(), 7)
        service.IDLE_TIMEOUT_SECONDS = 0
        service._close_debug_session = mock.AsyncMock()

        await service._close_after_idle()

        service._close_debug_session.assert_awaited_once_with("超过5分钟无操作")
