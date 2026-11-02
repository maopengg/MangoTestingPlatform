from src.apps.evaluation.schemas.case import EvaluationGraderBinding
from copy import deepcopy
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from src.apps.evaluation.api.serializers.execution import CaseExecutionListSerializer
from src.apps.evaluation.api.views.case import CaseViews
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.models import (
    EvaluationDataset,
    EvaluationDatasetVersion,
    EvaluationCase,
    EvaluationCaseExecution,
    EvaluationDatasetItem,
    EvaluationItemResult,
)
from src.apps.evaluation.schemas import EvaluationGradingConfig, GraderMetric, GraderResult
from src.apps.evaluation.services.graders import EvaluationGraderRegistry
from src.apps.evaluation.services.case import EvaluationCaseService
from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
from src.apps.test_center.models import ProjectProduct
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.models import User
from src.apps.user.services.permission import PermissionMenuService
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


def case_config():
    return {
        "schema_version": 1,
        "target": {"type": "script", "parameters": {"code": 'def main(input, context): return {"answer": "原输出"}'}},
        "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "accuracy"}]},
    }


class CaseFlowTests(SimpleTestCase):
    def test_case_can_bind_a_global_dataset_without_product_or_module(self):
        dataset = EvaluationDataset(pk=10, name='全局题库')
        version = EvaluationDatasetVersion(pk=11, dataset=dataset, status='published')
        values = {'project_product': ProjectProduct(pk=5), 'dataset_version': version, 'config': case_config()}
        with patch.object(EvaluationCaseService, 'selected_items', return_value=[]):
            self.assertEqual(EvaluationCaseService.normalize(values)['dataset_version'], version)

    def test_uncertain_judge_marks_invalid_without_creating_review_queue(self):
        row = EvaluationItemResult(pk=1, item_snapshot={"effective_graders": [{"binding_hash": "test-binding"}]})
        grader = MagicMock()
        grader.evaluate.return_value = GraderResult(
            metrics=[GraderMetric(key="accuracy", score=90, passed=False, confidence=0.2)],
            requires_review=True,
        )
        adapter = MagicMock()
        adapter.execute.return_value = {"output": {"answer": "答案"}}
        with (patch.object(EvaluationItemResult, "save"),
              patch.object(EvaluationItemResult, "grade_results", MagicMock()),
              patch("src.apps.evaluation.services.execution.EvaluationAttemptService.start", return_value=1),
              patch("src.apps.evaluation.services.execution.EvaluationAttemptService.finish"),
              patch.object(EvaluationCaseExecutionService, "_save_grade_results"),
              patch.object(EvaluationGraderRegistry, "resolve", return_value=(grader, {}))):
            EvaluationCaseExecutionService._execute_item_core(
                SimpleNamespace(created_by_id=1), row, SimpleNamespace(execution=SimpleNamespace(retry_count=0, item_timeout_seconds=600), grading=EvaluationGradingConfig.model_validate(case_config()["grading"]), grader_bindings={"test-binding": EvaluationGraderBinding(grader_key="exact_match",metric_key="accuracy")}),
                adapter, SimpleNamespace(executor_config={}), SimpleNamespace(), SimpleNamespace(),
            )
        self.assertEqual(row.verdict, "invalid")
        self.assertEqual(row.grade_status, "invalid")
        self.assertEqual(row.error_category, "judge_uncertain")

    def test_execution_list_does_not_include_snapshot_or_detailed_evidence(self):
        fields = CaseExecutionListSerializer().fields
        self.assertNotIn("snapshot", fields)
        self.assertNotIn("error_message", fields)
        summary = CaseExecutionListSerializer.get_summary(SimpleNamespace(summary={"average_score": 90, "metrics": {"private": 1}, "groups": {"private": 2}}))
        self.assertEqual(summary, {"average_score": 90})

    def case(self):
        product = ProjectProduct(pk=5)
        dataset = EvaluationDataset(pk=3)
        version = EvaluationDatasetVersion(pk=7, dataset=dataset, version_no=2, status="published", content_hash="dataset-hash")
        return EvaluationCase(pk=1, name="记忆评测", project_product=product, dataset_version=version,
                              status="enabled", config=case_config())

    def test_retired_routes_and_permissions_do_not_expand_access(self):
        for path in ["/api/evaluation/target", "/api/evaluation/review", "/api/evaluation/grader",
                     "/api/evaluation/case/1/versions", "/api/evaluation/case/version/1/publish"]:
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)
        valid = PermissionMenuService.all_permission_keys()
        for prefix in ("evaluation.target", "evaluation.review", "evaluation.plan", "evaluation.run", "evaluation.case:change"):
            self.assertFalse(any(key.startswith(prefix) for key in valid))
        self.assertIn("evaluation.case:change", valid)
        self.assertIn("graders", resolve("/api/evaluation/case/graders").func.actions.values())

    def test_case_rejects_cross_product_draft_and_unregistered_graders(self):
        case = self.case()
        with self.assertRaises(EvaluationError):
            EvaluationCaseService.normalize({"project_product": ProjectProduct(pk=8)}, case)
        case.dataset_version.status = "draft"
        with self.assertRaises(EvaluationError):
            EvaluationCaseService.normalize({}, case)
        case.dataset_version.status = "published"
        for key in ("manual", "unregistered"):
            with self.subTest(key=key), self.assertRaises(EvaluationError):
                EvaluationCaseService.normalize({"config": {**case_config(), "grading": {"default_graders": [{"grader_key": key, "metric_key": "score"}]}}}, case)
        self.assertEqual(EvaluationGraderRegistry.resolve("unregistered"), (None, {}))

    def test_model_judge_cannot_silently_replace_removed_calibration_gate(self):
        with self.assertRaises(EvaluationError):
            EvaluationCaseService.normalize({"config": {**case_config(), "grading": {"default_graders": [
                {"grader_key": "model_judge", "metric_key": "quality", "hard_gate": True},
                {"grader_key": "exact_match", "metric_key": "accuracy"},
            ]}}}, self.case())



    def test_execution_checks_target_business_permission(self):
        target = SimpleNamespace(target_type="api_case", project_product_id=5)
        for granted, permitted in [({"evaluation.case:change"}, False), ({"api.case:change"}, True)]:
            with patch("src.apps.evaluation.services.case.ensure_product_scope"), patch.object(PermissionMenuService, "permission_keys_for_user", return_value=granted):
                if permitted:
                    EvaluationCaseService.ensure_target_access(target, SimpleNamespace(id=2))
                else:
                    with self.assertRaises(EvaluationError):
                        EvaluationCaseService.ensure_target_access(target, SimpleNamespace(id=2))

    def test_status_and_content_permissions_are_independent(self):
        for data, grants, expected in [
            ({"id": 1, "status": "enabled"}, {"evaluation.case:change"}, True),
            ({"id": 1, "status": "enabled"}, {"evaluation.case:change"}, False),
            ({"id": 1, "status": "enabled", "name": "新名称"}, {"evaluation.case:change"}, False),
            ({"id": 1, "status": "enabled", "name": "新名称"}, {"evaluation.case:change", "evaluation.case:change"}, True),
        ]:
            request = SimpleNamespace(method="PUT", path="/api/evaluation/case", data=data, query_params={}, user=SimpleNamespace(user_obj=SimpleNamespace(id=2)))
            with self.subTest(data=data, grants=grants), patch.object(PermissionMenuService, "is_effective_super_admin", return_value=False), patch.object(PermissionMenuService, "permission_keys_for_user", return_value=grants):
                self.assertEqual(MenuActionPermission().has_permission(request, CaseViews()), expected)


class EvaluationDraftCaseTests(SimpleTestCase):
    def draft(self):
        return EvaluationCase(pk=99, name='未配置用例', project_product=ProjectProduct(pk=5), status='draft', config={})

    def test_create_metadata_without_dataset_or_config_is_a_draft(self):
        values = EvaluationCaseService.normalize({'name': '空白草稿', 'project_product': ProjectProduct(pk=5)})
        self.assertEqual(values['config'], {})
        self.assertNotIn('dataset_version', values)
        field = EvaluationCase._meta.get_field('dataset_version')
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_metadata_edits_do_not_require_or_overwrite_configuration(self):
        draft = self.draft()
        values = EvaluationCaseService.normalize({'name': '新名称', 'description': '只改基本信息'}, draft)
        self.assertEqual(values, {'name': '新名称', 'description': '只改基本信息'})
        self.assertEqual(draft.config, {})

    def test_unconfigured_case_cannot_be_enabled_or_executed(self):
        draft = self.draft()
        with self.assertRaises(EvaluationError):
            EvaluationCaseService.normalize({'status': 'enabled'}, draft)
        with patch('src.apps.evaluation.services.case.ensure_product_scope'):
            with self.assertRaises(EvaluationError):
                EvaluationCaseService.validate_execution(draft, SimpleNamespace())
            draft.status = 'enabled'
            with self.assertRaises(EvaluationError):
                EvaluationCaseService.validate_execution(draft, SimpleNamespace())
            with self.assertRaises(EvaluationError):
                EvaluationCaseService.grading_preview(draft, SimpleNamespace())

    def test_null_dataset_serializes_as_unconfigured_instead_of_failing(self):
        from src.apps.evaluation.api.serializers.case import CaseSerializer
        data = CaseSerializer(self.draft()).data
        self.assertIsNone(data['dataset_version'])
        self.assertIsNone(data['dataset_id'])
        self.assertIsNone(data['dataset_name'])
        self.assertIsNone(data['dataset_version_no'])
        self.assertFalse(CaseSerializer().fields['dataset_version'].required)

    def test_mcp_can_create_an_unconfigured_draft_with_explicit_product_scope(self):
        from src.apps.evaluation.services.assets import create_case
        with (patch('src.apps.evaluation.services.assets.ensure_product_scope') as scope,
              patch('src.apps.evaluation.services.assets.TestCenterQuerySelector.project_product') as products,
              patch.object(EvaluationCaseService, 'save') as save):
            products.return_value.filter.return_value.first.return_value = ProjectProduct(pk=5)
            create_case({'name': 'MCP 草稿', 'project_product_id': 5}, SimpleNamespace(id=2))
            scope.assert_called_once()
            values = save.call_args.kwargs['values']
            self.assertIsNone(values['dataset_version'])
            self.assertEqual(values['config'], {})
            self.assertEqual(values['project_product'].pk, 5)

    def test_mcp_cannot_create_an_unscoped_blank_case(self):
        from src.apps.evaluation.services.assets import create_case
        with self.assertRaises(EvaluationError):
            create_case({'name': '无归属草稿'}, SimpleNamespace(id=2))
