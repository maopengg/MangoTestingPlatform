import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ui.test_page_steps import TestPageSteps


class TestOpenTargetPage(unittest.IsolatedAsyncioTestCase):
    async def test_open_target_page_navigates_without_executing_steps(self):
        service = object.__new__(TestPageSteps)
        service.lock = asyncio.Lock()
        service.base_data = SimpleNamespace(
            locator_engine=None,
            page=SimpleNamespace(
                url='https://example.test/target',
                goto=AsyncMock(),
            ),
        )
        service.web_runtime = object()
        service._cancel_idle_close = MagicMock()
        service._use_debug_session = AsyncMock()
        service.refresh_runtime_config = AsyncMock()
        service.apply_ui_auth_cache = AsyncMock()
        service._schedule_idle_close = MagicMock()
        service._reset_runtime_base_data = MagicMock()
        data = SimpleNamespace(id=8, name='目标页面', test_env=2)

        page_steps = MagicMock()
        page_steps.driver_init = AsyncMock()
        page_steps.page_init = AsyncMock()
        page_steps._resolve_step_url.return_value = 'https://example.test/target'

        with patch(
            'src.services.ui.test_page_steps.PageSteps',
            return_value=page_steps,
        ):
            await service.open_target_page(data)

        page_steps.driver_init.assert_awaited_once()
        page_steps.page_init.assert_awaited_once()
        service.base_data.page.goto.assert_awaited_once_with(
            'https://example.test/target',
            wait_until='domcontentloaded',
            timeout=30000,
        )
        self.assertFalse(hasattr(page_steps, 'steps_main') and page_steps.steps_main.called)
        service._schedule_idle_close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
