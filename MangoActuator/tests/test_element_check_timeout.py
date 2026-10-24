import asyncio
import unittest
from types import SimpleNamespace

from src.services.ui.test_page_steps import TestPageSteps


class ElementCheckTimeoutTest(unittest.IsolatedAsyncioTestCase):
    async def test_check_element_cancels_stalled_detection_at_service_deadline(self):
        service = object.__new__(TestPageSteps)
        service.lock = asyncio.Lock()
        service.ELEMENT_CHECK_TIMEOUT_SECONDS = 0.01
        service._cancel_idle_close = lambda: None
        cancelled = asyncio.Event()

        async def stalled_check(_data):
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled.set()

        service._check_element = stalled_check

        await service.check_element(SimpleNamespace(check_id='timeout-check'))

        self.assertTrue(cancelled.is_set())


if __name__ == '__main__':
    unittest.main()
