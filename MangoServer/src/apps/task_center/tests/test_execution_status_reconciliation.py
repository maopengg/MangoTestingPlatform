from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.system.enums import (
    ExecutorTaskStatusEnum,
    ExecutorTaskTypeEnum,
    ServerApiCommandEnum,
    ServerPytestCommandEnum,
    ServerUiCommandEnum,
)
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.task_center.services.execution.status_reconciliation import (
    ExecutionStatusProjectionService,
)
from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.test_suite.timeout_recovery import (
    TestSuiteTimeoutRecoveryService,
)


class ExecutionStatusProjectionTests(SimpleTestCase):
    @staticmethod
    def task(**overrides):
        values = {
            "id": 10,
            "business_id": 20,
            "business_type": ServerApiCommandEnum.API_CASE.value,
            "status": ExecutorTaskStatusEnum.SUCCESS.value,
            "result_data": {"status": TaskEnum.WARNING.value},
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    @patch.object(ExecutionStatusProjectionService, "_has_newer_task", return_value=False)
    @patch(
        "src.apps.auto_api.services.test_case.run_status."
        "ApiCaseRunStatusService.project_status"
    )
    def test_api_case_projects_result_status(self, project_status, _has_newer_task):
        project_status.return_value = 2

        updated = ExecutionStatusProjectionService.project(self.task())

        self.assertEqual(updated, 2)
        project_status.assert_called_once_with(20, TaskEnum.WARNING.value)

    @patch.object(ExecutionStatusProjectionService, "_has_newer_task", return_value=True)
    def test_older_task_never_overwrites_newer_execution(self, _has_newer_task):
        updated = ExecutionStatusProjectionService.project(self.task())

        self.assertEqual(updated, 0)

    @patch.object(ExecutionStatusProjectionService, "_has_newer_task", return_value=False)
    @patch(
        "src.apps.auto_ui.services.execution_status."
        "UiExecutionStatusService.project_case_status"
    )
    def test_terminal_failure_marks_ui_case_failed(self, project_status, _has_newer_task):
        project_status.return_value = 1
        task = self.task(
            business_type=ServerUiCommandEnum.CASE_BATCH.value,
            status=ExecutorTaskStatusEnum.INTERRUPTED.value,
            result_data=None,
        )

        updated = ExecutionStatusProjectionService.project(task, force_failure=True)

        self.assertEqual(updated, 1)
        project_status.assert_called_once_with(20, TaskEnum.FAIL.value)

    @patch.object(ExecutionStatusProjectionService, "project")
    def test_executor_recovery_uses_shared_terminal_projection(self, project):
        task = self.task(
            business_type=ServerPytestCommandEnum.TEST_CASE.value,
            status=ExecutorTaskStatusEnum.TIMEOUT.value,
        )

        ExecutorTaskService._project_terminal_failure(task, "执行超时")

        project.assert_called_once_with(task, force_failure=True)

    @patch(
        "src.apps.auto_api.services.test_case.run_status."
        "ApiCaseRunStatusService.project_status"
    )
    def test_api_completion_projects_immediately(self, project_status):
        task = self.task(
            task_type="api_execution",
            result_data={"status": TaskEnum.SUCCESS.value},
        )

        ExecutorTaskService._project_business_result(
            task,
            {"status": TaskEnum.SUCCESS.value},
            success=True,
        )

        project_status.assert_called_once_with(20, TaskEnum.SUCCESS.value)

    @patch.object(ExecutionStatusProjectionService, "project", return_value=1)
    @patch.object(ExecutionStatusProjectionService, "_latest_tasks")
    @patch.object(ExecutionStatusProjectionService, "_candidate_sources")
    def test_reconciliation_starts_from_proceeding_business_records(
            self,
            candidate_sources,
            latest_tasks,
            project,
    ):
        business_updated_at = timezone.now() - timedelta(minutes=4)
        loader = lambda limit: [(20, business_updated_at)]
        task = self.task(
            finished_at=timezone.now() - timedelta(minutes=3),
        )
        candidate_sources.return_value = [(ServerApiCommandEnum.API_CASE.value, loader)]
        latest_tasks.return_value = [task]

        result = ExecutionStatusProjectionService.reconcile(batch_size=10)

        latest_tasks.assert_called_once_with(ServerApiCommandEnum.API_CASE.value, [20])
        project.assert_called_once_with(task)
        self.assertEqual(result["projected_count"], 1)

    @patch.object(ExecutionStatusProjectionService, "project", return_value=1)
    @patch.object(ExecutionStatusProjectionService, "_latest_tasks")
    @patch.object(ExecutionStatusProjectionService, "_candidate_sources")
    def test_reconciliation_does_not_apply_an_older_task_to_a_new_run(
            self,
            candidate_sources,
            latest_tasks,
            project,
    ):
        task = self.task(finished_at=timezone.now() - timedelta(minutes=3))
        loader = lambda limit: [(20, timezone.now() - timedelta(minutes=1))]
        candidate_sources.return_value = [(ServerApiCommandEnum.API_CASE.value, loader)]
        latest_tasks.return_value = [task]

        result = ExecutionStatusProjectionService.reconcile(batch_size=10)

        project.assert_not_called()
        self.assertEqual(result["skipped_count"], 1)

    @patch(
        "src.apps.auto_pytest.services.execution_status."
        "PytestExecutionStatusService.project_status"
    )
    def test_test_suite_timeout_projects_pytest_business_status(self, project_status):
        detail = SimpleNamespace(
            type=TestCaseTypeEnum.PYTEST.value,
            case_id=35,
        )

        TestSuiteTimeoutRecoveryService.project_business_status(
            detail,
            TaskEnum.FAIL.value,
        )

        project_status.assert_called_once_with(35, TaskEnum.FAIL.value)


class ExecutionStatusSystemJobTests(SimpleTestCase):
    def test_pytest_and_ui_case_execution_timeout_is_one_hour(self):
        self.assertEqual(
            ExecutorTaskService.policy(
                ExecutorTaskTypeEnum.PYTEST_EXECUTION.value,
            ).execution_timeout_seconds,
            60 * 60,
        )
        self.assertEqual(
            ExecutorTaskService.policy(
                ExecutorTaskTypeEnum.UI_CASE.value,
            ).execution_timeout_seconds,
            60 * 60,
        )

    def test_legacy_update_time_jobs_are_replaced_by_reconciliation(self):
        keys = {job.key for job in SystemJobService.JOBS}

        self.assertIn("recover_executor_tasks", keys)
        self.assertIn("repair_test_suite_status", keys)
        self.assertIn("reconcile_execution_statuses", keys)
        self.assertTrue({
                            "repair_api_case_status",
                            "repair_ui_case_status",
                            "repair_ui_page_step_status",
                            "repair_pytest_case_status",
                        }.isdisjoint(keys))
