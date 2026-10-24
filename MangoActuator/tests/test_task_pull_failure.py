import unittest
from unittest.mock import patch

from src.network.http.apis.base import ApiError
from src.services.task_pull_failure import TaskPullFailureReporter


class TaskPullFailureReporterTest(unittest.TestCase):
    def setUp(self):
        TaskPullFailureReporter._failures.clear()

    def test_same_failure_is_logged_once_per_interval(self):
        error = ApiError('<html>Server Error</html>', status_code=500)
        with patch('src.services.task_pull_failure.time.time', side_effect=[1, 10, 62]), \
                patch('src.services.task_pull_failure.log.warning') as warning:
            TaskPullFailureReporter.report('UI', error)
            TaskPullFailureReporter.report('UI', error)
            TaskPullFailureReporter.report('UI', error)

        self.assertEqual(warning.call_count, 2)
        self.assertIn('HTTP 500', warning.call_args_list[0].args[0])
        self.assertNotIn('<html>', warning.call_args_list[0].args[0])

    def test_recovery_is_logged_once(self):
        TaskPullFailureReporter._failures['UI'] = {'summary': 'HTTP 500'}
        with patch('src.services.task_pull_failure.log.info') as info:
            TaskPullFailureReporter.recovered('UI')
            TaskPullFailureReporter.recovered('UI')
        info.assert_called_once_with('HTTP拉取UI任务已恢复')


if __name__ == '__main__':
    unittest.main()
