import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mangoautomation.enums import ElementOperationEnum
from mangotools.models import MethodModel

from src.enums.tools_enum import StatusEnum
from src.services.ui.page_steps import PageSteps


class ForceWaitNodeTest(unittest.IsolatedAsyncioTestCase):
    async def test_force_wait_runs_in_actuator_without_browser(self):
        service = PageSteps.__new__(PageSteps)
        element = SimpleNamespace(
            id=12,
            name=None,
            ope_value=[MethodModel(f='seconds', v=0.25)],
        )

        with patch('src.services.ui.page_steps.asyncio.sleep', new=AsyncMock()) as sleep:
            result = await service._execute_force_wait_element(element)

        sleep.assert_awaited_once_with(0.25)
        self.assertEqual(result.type, ElementOperationEnum.FORCE_WAIT.value)
        self.assertEqual(result.status, StatusEnum.SUCCESS.value)
        self.assertEqual(result.name, '强制等待 0.25 秒')

    async def test_force_wait_rejects_invalid_runtime_value(self):
        service = PageSteps.__new__(PageSteps)
        element = SimpleNamespace(
            id=13,
            name='强制等待',
            ope_value=[MethodModel(f='seconds', v=4000)],
        )

        result = await service._execute_force_wait_element(element)

        self.assertEqual(result.status, StatusEnum.FAIL.value)
        self.assertIn('0 到 3600 秒', result.error_message)


if __name__ == '__main__':
    unittest.main()
