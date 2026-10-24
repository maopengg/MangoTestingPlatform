import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.ui.test_page_steps import TestPageSteps


class TestPageStepAuthCache(unittest.IsolatedAsyncioTestCase):
    async def test_new_context_always_receives_auth_cache(self):
        service = object.__new__(TestPageSteps)
        first_context = object()
        second_context = object()
        service.base_data = SimpleNamespace(context=first_context, page=object())
        service.web_runtime = object()
        service._ui_auth_applied_context = None
        data = MagicMock(ui_auth_cache=object())

        with patch(
            'src.services.ui.test_page_steps.UiAuthCacheApplier.apply',
            new_callable=AsyncMock,
        ) as apply:
            await service.apply_ui_auth_cache(data)
            await service.apply_ui_auth_cache(data)
            service.base_data.context = second_context
            await service.apply_ui_auth_cache(data)

        self.assertEqual(apply.await_count, 2)
        self.assertIs(service._ui_auth_applied_context, second_context)


if __name__ == '__main__':
    unittest.main()
