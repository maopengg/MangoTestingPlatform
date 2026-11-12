import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from playwright._impl._errors import TimeoutError

from src.services.ui.test_page_steps import TestPageSteps


class AutoAuthSessionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        TestPageSteps._auth_sessions.clear()

    def tearDown(self):
        TestPageSteps._auth_sessions.clear()

    async def test_failed_capture_preserves_login_session_for_retry(self):
        data = SimpleNamespace(config_id=9, send_user='tester')
        key = ('tester', 9)
        base_data = SimpleNamespace(page=object(), context=object())
        TestPageSteps._auth_sessions[key] = base_data
        service = object.__new__(TestPageSteps)
        service.send_steps_result = AsyncMock()
        service._collect_auth_cache = AsyncMock(side_effect=[TimeoutError('temporary failure'), {'cookies': []}])
        with patch('src.services.ui.test_page_steps.AutomationSessionManager.close_page_context', new=AsyncMock()) as close:
            with self.assertRaises(TimeoutError):
                await service.capture_auto_auth(data)
            self.assertIs(TestPageSteps._auth_sessions[key], base_data)
            close.assert_not_awaited()
            result = await service.capture_auto_auth(data)
            self.assertEqual(result, {'config_id': 9, 'cache_data': {'cookies': []}})
            close.assert_awaited_once()
            self.assertNotIn(key, TestPageSteps._auth_sessions)

    async def test_capture_reuses_session_created_by_another_service_instance(self):
        config_id = 3
        page = SimpleNamespace()
        context = SimpleNamespace()
        base_data = SimpleNamespace(page=None, context=None)
        data = SimpleNamespace(
            config_id=config_id,
            url=None,
            send_user='maopeng',
        )
        session_key = ('maopeng', config_id)
        start_service = object.__new__(TestPageSteps)
        start_service.send_steps_result = AsyncMock()

        async def ensure_page(target, _runtime):
            target.page = page
            target.context = context

        start_service._ensure_web_page = AsyncMock(side_effect=ensure_page)

        with patch(
            'src.services.ui.test_page_steps.AutomationSessionManager.create_base_data',
            return_value=base_data,
        ), patch(
            'src.services.ui.test_page_steps.AutomationSessionManager.web_runtime',
            return_value=object(),
        ):
            await start_service.start_auto_auth(data)

        self.assertIs(TestPageSteps._auth_sessions[session_key], base_data)

        capture_service = object.__new__(TestPageSteps)
        capture_service.send_steps_result = AsyncMock()
        capture_service._collect_auth_cache = AsyncMock(return_value={'cookies': []})

        with patch(
            'src.services.ui.test_page_steps.AutomationSessionManager.close_page_context',
            new=AsyncMock(),
        ) as close_page_context:
            result = await capture_service.capture_auto_auth(data)

        capture_service._collect_auth_cache.assert_awaited_once_with(data, base_data)
        self.assertEqual(result, {'config_id': config_id, 'cache_data': {'cookies': []}})
        self.assertEqual(capture_service.send_steps_result.await_args.args[0], 200)
        close_page_context.assert_awaited_once_with(base_data, 'UI自动授权')
        self.assertNotIn(session_key, TestPageSteps._auth_sessions)


if __name__ == '__main__':
    unittest.main()
