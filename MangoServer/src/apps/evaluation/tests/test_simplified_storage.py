from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from src.apps.evaluation.api.serializers.item_result import ItemResultSerializer
from src.apps.evaluation.enums import (
    EvaluationExecutionStatusEnum,
    EvaluationGradeStatusEnum,
    EvaluationTriggerTypeEnum,
)
from pydantic import ValidationError
from src.apps.evaluation.exceptions import (
    EVALUATION_ATTEMPT_NOT_FOUND,
    EVALUATION_EXECUTION_FAILED,
    EvaluationError,
)
from src.apps.evaluation.models import EvaluationItemResult
from src.apps.evaluation.schemas.attempt import EvaluationAttemptRecord
from src.apps.evaluation.schemas.execution import EvaluationCaseExecutionCreate
from src.apps.evaluation.selectors.version import current_version, item_count
from src.apps.evaluation.services.execution.attempt import EvaluationAttemptService
from src.apps.evaluation.services.execution.execution import EvaluationCaseExecutionService
from src.apps.user.services.authorization.permission import PermissionMenuService
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class SimplifiedEvaluationStorageTests(SimpleTestCase):
    def test_execution_retries_and_timeout_keep_persisted_attempt_evidence(self):
        start = EvaluationAttemptService.start.__wrapped__
        finish = EvaluationAttemptService.finish.__wrapped__
        for timeout in (False, True):
            with self.subTest(timeout=timeout):
                row = EvaluationItemResult(pk=9, attempts=[])
                adapter = MagicMock()
                if timeout:
                    adapter.execute.return_value = {"output": {"answer": "结果"}}
                else:
                    adapter.execute.side_effect = EvaluationError(EVALUATION_EXECUTION_FAILED)
                config = SimpleNamespace(execution=SimpleNamespace(retry_count=2, item_timeout_seconds=1))
                with (
                    patch.object(EvaluationItemResult.objects, "select_for_update") as locked,
                    patch.object(EvaluationItemResult, "save"),
                    patch.object(EvaluationItemResult, "grade_results", MagicMock()),
                    patch.object(EvaluationCaseExecutionService, "_save_grade_results"),
                    patch.object(EvaluationAttemptService, "start", side_effect=start),
                    patch.object(EvaluationAttemptService, "finish", side_effect=finish),
                          patch("src.apps.evaluation.services.execution.execution.time.monotonic", side_effect=[0, 0, 0, 2, 2] if timeout else None, return_value=0),
                ):
                    locked.return_value.get.return_value = row
                    EvaluationCaseExecutionService._execute_item_core(
                        SimpleNamespace(created_by_id=1), row, config, adapter,
                        SimpleNamespace(executor_config={}), SimpleNamespace(), SimpleNamespace(),
                    )
                self.assertEqual(row.verdict, "invalid")
                self.assertEqual(len(row.attempts), 1 if timeout else 3)
                self.assertEqual(row.execution_status, "timeout" if timeout else "failed")
                self.assertTrue(all(item["status"] == row.execution_status for item in row.attempts))
                if timeout:
                    self.assertEqual(row.attempts[0]["output_snapshot"], {"answer": "结果"})

    def test_removed_schedule_endpoint_has_no_http_entry(self):
        with self.assertRaises(Resolver404):
            resolve("/api/evaluation/schedule")

    def test_schedule_permissions_retire_without_granting_task_center_access(self):
        valid = PermissionMenuService.all_permission_keys()
        self.assertFalse(any(key.startswith("evaluation.schedule") for key in valid))
        routes = PermissionMenuService.permission_tree()
        self.assertTrue(any(item["menuUrl"] == "/timing" for item in routes))
        with patch("src.apps.user.services.authorization.role_authorization.RoleAuthorizationService.get",
                   return_value={'version': 1, 'menu_keys': ['evaluation.schedule', 'evaluation.case'],
                                 'endpoint_permissions': {}}), patch(
                   'src.apps.user.services.authorization.permission.Role.objects.filter') as roles:
            roles.return_value.exists.return_value = False
            keys = PermissionMenuService.role_permission_keys(4)
        self.assertIn("evaluation.case", keys)
        self.assertFalse(any(key.startswith("evaluation.schedule") for key in keys))
        self.assertFalse(any(key.startswith("timing") for key in keys))

    def test_recovery_appends_and_finishing_old_attempt_preserves_new_history(self):
        stored = EvaluationItemResult(pk=9, attempts=[])
        first_worker = EvaluationItemResult(pk=9)
        second_worker = EvaluationItemResult(pk=9)
        with patch.object(EvaluationItemResult.objects, "select_for_update") as locked, patch.object(EvaluationItemResult, "save"):
            locked.return_value.get.return_value = stored
            first = EvaluationAttemptService.start.__wrapped__(first_worker)
            second = EvaluationAttemptService.start.__wrapped__(second_worker)
            EvaluationAttemptService.finish.__wrapped__(
                first_worker, first, status=EvaluationExecutionStatusEnum.FAILED,
                error_category="target_execution_failed", error_message="执行失败",
            )
        self.assertEqual([row["attempt_no"] for row in stored.attempts], [1, 2])
        self.assertEqual(stored.attempts[0]["status"], "failed")
        self.assertEqual(stored.attempts[1]["status"], "running")
        self.assertEqual(second, 2)
        for row in stored.attempts:
            EvaluationAttemptRecord.model_validate(row)

    def test_missing_attempt_is_business_error_without_saving(self):
        stored = EvaluationItemResult(pk=9, attempts=[])
        with patch.object(EvaluationItemResult.objects, "select_for_update") as locked, patch.object(EvaluationItemResult, "save") as save:
            locked.return_value.get.return_value = stored
            with self.assertRaises(EvaluationError) as caught:
                EvaluationAttemptService.finish.__wrapped__(stored, 8, status="failed")
        self.assertEqual(caught.exception.code, EVALUATION_ATTEMPT_NOT_FOUND.code)
        save.assert_not_called()

    def test_sample_response_has_one_source_for_metrics_and_attempts(self):
        row = EvaluationItemResult(pk=9, attempts=[])
        with patch.object(EvaluationItemResult, "grade_results", MagicMock()) as metrics:
            metrics.all.return_value = []
            data = ItemResultSerializer(row).data
        self.assertEqual(data["attempts"], [])
        self.assertEqual(data["grades"], [])
        self.assertNotIn("attempt_no", data)
        self.assertNotIn("metric_summary", data)

    def test_removed_workflows_are_not_advertised_or_accepted(self):
        self.assertEqual({item.value for item in EvaluationGradeStatusEnum}, {
            "pending", "grading", "graded", "invalid", "failed",
        })
        allowed = {"manual", "api", "retry"}
        self.assertEqual({item.value for item in EvaluationTriggerTypeEnum}, allowed)
        EvaluationCaseExecutionCreate.model_validate({"case_id": 1, "test_env": 1})
        for trigger in ("schedule", "pipeline"):
            with self.subTest(trigger=trigger), self.assertRaises(ValidationError):
                EvaluationCaseExecutionCreate.model_validate({"case_id": 1, "test_env": 1, "trigger_type": trigger})

    def test_annotated_statistics_do_not_issue_per_row_queries(self):
        asset = SimpleNamespace(published_version_no=3, versions=MagicMock())
        version = SimpleNamespace(enabled_item_count=7, items=MagicMock())
        self.assertEqual(current_version(asset), 3)
        self.assertEqual(item_count(version), 7)
        asset.versions.filter.assert_not_called()
        version.items.filter.assert_not_called()
