import unittest

from src.storage.sqlite import ExecutionCaseQueue


class ExecutionCaseQueueStopTests(unittest.TestCase):
    def test_extracts_ui_and_pytest_report_ids(self):
        self.assertEqual(
            ExecutionCaseQueue._extract_test_suite_id('{"test_suite_id": 123}'),
            123,
        )
        self.assertEqual(
            ExecutionCaseQueue._extract_test_suite_id('{"test_suite": "456"}'),
            456,
        )

    def test_invalid_payload_has_no_report_id(self):
        self.assertIsNone(ExecutionCaseQueue._extract_test_suite_id('not-json'))
        self.assertIsNone(ExecutionCaseQueue._extract_test_suite_id('{}'))


if __name__ == '__main__':
    unittest.main()
