import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.services.ui.test_page_steps import TestPageSteps


class AutoAuthSessionTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        TestPageSteps._auth_sessions.clear()

    def tearDown(self):
        TestPageSteps._auth_sessions.clear()

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
            'src.services.ui.test_page_steps.socket_conn.async_send',
            new=AsyncMock(),
        ) as async_send, patch(
            'src.services.ui.test_page_steps.AutomationSessionManager.close_page_context',
            new=AsyncMock(),
        ) as close_page_context:
            await capture_service.capture_auto_auth(data)

        capture_service._collect_auth_cache.assert_awaited_once_with(data, base_data)
        async_send.assert_awaited_once()
        close_page_context.assert_awaited_once_with(base_data, 'UI自动授权')
        self.assertNotIn(session_key, TestPageSteps._auth_sessions)


if __name__ == '__main__':
    unittest.main()
