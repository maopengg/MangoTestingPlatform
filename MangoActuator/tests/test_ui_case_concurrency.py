import unittest
from unittest.mock import patch

from src.services.ui.case_concurrency import UiCaseConcurrency


class UiCaseConcurrencyTest(unittest.TestCase):
    def setUp(self):
        UiCaseConcurrency.reset()

    def tearDown(self):
        UiCaseConcurrency.reset()

    def test_two_task_channels_share_configured_capacity(self):
        with patch(
                "src.services.ui.case_concurrency.SetConfig.get_web_parallel",
                return_value=2,
        ):
            self.assertTrue(UiCaseConcurrency.acquire())
            self.assertTrue(UiCaseConcurrency.acquire())
            self.assertFalse(UiCaseConcurrency.acquire())
            self.assertEqual(UiCaseConcurrency.available(), 0)

            UiCaseConcurrency.release()

            self.assertEqual(UiCaseConcurrency.available(), 1)
            self.assertTrue(UiCaseConcurrency.acquire())

    def test_capacity_follows_runtime_configuration(self):
        with patch(
                "src.services.ui.case_concurrency.SetConfig.get_web_parallel",
                return_value=8,
        ):
            self.assertEqual(UiCaseConcurrency.capacity(), 8)
            self.assertEqual(UiCaseConcurrency.available(), 8)

    def test_reserve_is_atomic_and_never_exceeds_capacity(self):
        with patch(
                "src.services.ui.case_concurrency.SetConfig.get_web_parallel",
                return_value=3,
        ):
            self.assertEqual(UiCaseConcurrency.reserve(2), 2)
            self.assertEqual(UiCaseConcurrency.reserve(2), 1)
            self.assertEqual(UiCaseConcurrency.running(), 3)

            UiCaseConcurrency.release(2)

            self.assertEqual(UiCaseConcurrency.running(), 1)
            self.assertEqual(UiCaseConcurrency.available(), 2)


if __name__ == "__main__":
    unittest.main()
