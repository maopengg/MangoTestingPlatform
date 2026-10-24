from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from django.urls import resolve
from pydantic import ValidationError
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.schemas.case import EvaluationGraderBinding, EvaluationGradingConfig
from src.apps.evaluation.schemas.grader import ModelJudgeOutput
from src.apps.evaluation.services.grading import resolve_graders, validate_bindings
from src.apps.evaluation.services.adapters import BaseTargetAdapter
from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
from src.apps.evaluation.services.target_input import compile_target_input
from src.apps.evaluation.selectors.execution import get_execution
from src.apps.evaluation.models import EvaluationGradeResult
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService
from src.apps.evaluation.formatters.payload import content_hash
from src.apps.evaluation.api.views.execution import CaseExecutionViews
from src.apps.evaluation.services.case import EvaluationCaseService
from src.apps.evaluation.models import EvaluationCase, EvaluationDatasetItem, EvaluationDatasetVersion
from src.apps.evaluation.services.importing import EvaluationApiCaseImportService


class EvaluationCaseContractTests(SimpleTestCase):
    def test_api_import_invalidates_previous_quality_acknowledgement(self):
        version = SimpleNamespace(status="draft", dataset=SimpleNamespace(project_product_id=1))
        source = SimpleNamespace(id=1, name="source", level=1, scenario_tags=[], parametrize=[{"question": "q", "expected": {"answer": "a"}}])
        item = EvaluationDatasetItem(pk=3)
        item.save = MagicMock()
        with patch.object(EvaluationDatasetVersion.objects, "select_for_update") as locked, patch("src.apps.evaluation.services.importing.scope_queryset") as cases, patch("src.apps.evaluation.services.importing.EvaluationApiCaseImportService.ensure_source_access"), patch("src.apps.evaluation.services.importing.ensure_dataset_access"), patch.object(EvaluationDatasetItem.objects, "update_or_create", return_value=(item, True)), patch("src.apps.evaluation.services.importing.EvaluationVersionService.validate_item"), patch("src.apps.evaluation.services.dataset_item.EvaluationDatasetItemService.reset_quality_ack") as reset:
            locked.return_value.select_related.return_value.filter.return_value.first.return_value = version
            cases.return_value.order_by.return_value = [source]
            result = EvaluationApiCaseImportService.import_cases.__wrapped__(EvaluationApiCaseImportService, 1, [1], user=SimpleNamespace(id=1))
            self.assertEqual(result["imported_count"], 1)
            reset.assert_called_once_with(version)

    def test_api_import_cannot_bypass_source_case_permission(self):
        for keys, allowed in [({"evaluation.dataset:import"}, False), ({"api.case:detail"}, True)]:
            with self.subTest(keys=keys), patch.object(PermissionMenuService, "permission_keys_for_user", return_value=keys):
                if allowed:
                    EvaluationApiCaseImportService.ensure_source_access(SimpleNamespace(id=1))
                else:
                    with self.assertRaises(EvaluationError):
                        EvaluationApiCaseImportService.ensure_source_access(SimpleNamespace(id=1))
    def test_item_replacement_preserves_required_checks(self):
        grading = EvaluationGradingConfig.model_validate({
            "default_graders": [{"grader_key": "exact_match", "metric_key": "default"}],
            "required_graders": [{"grader_key": "json_schema", "metric_key": "schema", "hard_gate": True}],
        })
        inherited = resolve_graders(grading, {})
        replaced = resolve_graders(grading, {"mode": "replace", "graders": [{"grader_key": "contains", "metric_key": "custom"}]})
        self.assertEqual([(row.metric_key, source) for row, source in inherited], [("default", "default"), ("schema", "required")])
        self.assertEqual([(row.metric_key, source) for row, source in replaced], [("custom", "override"), ("schema", "required")])

    def test_conflicting_override_cannot_shadow_required_metric(self):
        grading = EvaluationGradingConfig.model_validate({"required_graders": [{"grader_key": "exact_match", "metric_key": "same"}]})
        with self.assertRaises(EvaluationError):
            resolve_graders(grading, {"mode": "replace", "graders": [{"grader_key": "contains", "metric_key": "same"}]})

    def test_derived_metric_collision_is_rejected(self):
        with self.assertRaises(EvaluationError):
            validate_bindings([EvaluationGraderBinding(grader_key="set_match", metric_key="items"),
                               EvaluationGraderBinding(grader_key="exact_match", metric_key="items_precision")])

    def test_nan_parameters_are_not_a_valid_configuration(self):
        with self.assertRaises(EvaluationError):
            validate_bindings([EvaluationGraderBinding(grader_key="numeric_tolerance", metric_key="number", parameters={"absolute_tolerance": float("nan")})])

    def test_judge_requires_explicit_finite_structured_evidence(self):
        valid = {"score": 90.0, "passed": True, "confidence": 0.9, "requires_review": False, "reason": "matched", "evidence": {"reference": "answer"}}
        ModelJudgeOutput.model_validate(valid)
        for change in ({"score": float("nan")}, {"score": 101}, {"passed": "false"}, {"confidence": 2}, {"requires_review": "false"}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ModelJudgeOutput.model_validate({**valid, **change})
        with self.assertRaises(ValidationError):
            ModelJudgeOutput.model_validate({})

    def test_target_mapping_cannot_read_gold_or_hidden_context(self):
        item = SimpleNamespace(input_data={"question": "who"}, expected_output={"answer": "gold"},
                               context={"hidden": "secret", "target_visible": {"hint": "public"}}, metadata={"split": "test"})
        self.assertEqual(compile_target_input(item, "question"), {"question": {"question": "who"}})
        self.assertEqual(compile_target_input(item), {"case_input": {"question": "who"}})

    def test_external_errors_are_not_capacity_scores_but_business_answers_are(self):
        for code in (None, 401, 403, 408, 429, 503):
            with self.subTest(code=code), self.assertRaises(EvaluationError):
                BaseTargetAdapter.ensure_response_available({"code": code}, failed=True)
        for code in (200, 400, 404, 422):
            BaseTargetAdapter.ensure_response_available({"code": code}, failed=True)

    def test_unavailable_sse_stream_is_not_sent_to_grader(self):
        response = {"code": 200, "request_protocol_type": "sse", "sse_events": [{"data": "answer"}], "sse_stop_reason": "end_event"}
        BaseTargetAdapter.ensure_response_available(response)
        for changes in ({"code": 400, "call_success": False}, {"sse_events": []}, {"sse_stop_reason": "timeout"}, {"sse_stop_reason": "max_duration"}, {"sse_stop_reason": "max_event_count"}):
            with self.subTest(changes=changes), self.assertRaises(EvaluationError):
                BaseTargetAdapter.ensure_response_available({**response, **changes}, failed=changes.get("call_success") is False)

    def test_different_grader_parameters_have_separate_metric_summaries(self):
        values = [{"item_result__dataset_item_id": "Q1", "score": 100, "passed": True, "grader_key": "exact_match", "grader_version": 1, "grading_snapshot": {"binding_hash": "a", "metric": "accuracy"}},
                  {"item_result__dataset_item_id": "Q2", "score": 0, "passed": False, "grader_key": "exact_match", "grader_version": 1, "grading_snapshot": {"binding_hash": "b", "metric": "accuracy"}}]
        with patch.object(EvaluationGradeResult.objects, "filter") as query:
            query.return_value.values.return_value = values
            summary = EvaluationCaseExecutionService._metric_summary(SimpleNamespace(id=1))
        self.assertIsNone(summary["accuracy"]["average_score"])
        self.assertEqual({item["binding_hash"] for item in summary["accuracy"]["variants"]}, {"a", "b"})

    def test_nested_execution_lookup_does_not_accept_another_case(self):
        with patch("src.apps.evaluation.selectors.execution.case_executions") as query:
            query.return_value.filter.return_value.first.return_value = None
            with self.assertRaises(EvaluationError):
                get_execution(10, 20, SimpleNamespace(id=1))
            query.assert_called_once_with(10, SimpleNamespace(id=1))
            query.return_value.filter.assert_called_once_with(pk=20)

    def test_result_routes_require_detail_not_execute_or_guest(self):
        route = resolve("/api/evaluation/case/1/executions/2/items/3")
        for keys, allowed in [({"evaluation.case:execute"}, False), ({"evaluation.case"}, False), ({"evaluation.case:detail"}, True), (set(), False)]:
            view = route.func.cls(); view.action = route.func.actions["get"]
            request = SimpleNamespace(method="GET", path="/api/evaluation/case/1/executions/2/items/3", data={}, query_params={}, user=SimpleNamespace(user_obj=SimpleNamespace(id=1)))
            with self.subTest(keys=keys), patch.object(PermissionMenuService, "is_effective_super_admin", return_value=False), patch.object(PermissionMenuService, "permission_keys_for_user", return_value=keys):
                self.assertEqual(MenuActionPermission().has_permission(request, view), allowed)

    def test_execution_receipt_does_not_disclose_snapshot_to_execute_only_role(self):
        request = SimpleNamespace(data={"test_env": 1}, headers={}, user=SimpleNamespace(user_obj=SimpleNamespace(id=1)))
        record = SimpleNamespace(id=9, execution_no="EV-example", status="pending", snapshot={"gold": "private"})
        with patch("src.apps.evaluation.api.views.execution.get_case"), patch.object(EvaluationCaseExecutionService, "create", return_value=record), patch.object(EvaluationCaseExecutionService, "submit"):
            response = CaseExecutionViews().create(request, case_id=1)
        self.assertEqual(response.data["data"], {"id": 9, "execution_no": "EV-example", "status": "pending"})

    def test_manifest_and_frozen_items_are_checked_before_execution(self):
        row = SimpleNamespace(dataset_item_id=101, item_snapshot={"id": 101, "input_data": {"q": "first"}})
        snapshot = {"selection": {"item_ids": [101], "scope": "full", "items_hash": content_hash([row.item_snapshot])}, "signatures": {}}
        snapshot["signatures"]["manifest"] = content_hash(snapshot)
        EvaluationCaseExecutionService._validate_snapshot(snapshot, [row, row])
        row.item_snapshot = {"input_data": {"q": "tampered"}}
        with self.assertRaises(EvaluationError):
            EvaluationCaseExecutionService._validate_snapshot(snapshot, [row])
        snapshot["selection"]["scope"] = "tampered"
        with self.assertRaises(EvaluationError):
            EvaluationCaseExecutionService._validate_snapshot(snapshot, [row])

    def test_draft_case_can_validate_without_executing_target(self):
        config = {"target": {"type": "script"}, "grading": {"default_graders": [{"grader_key": "exact_match", "metric_key": "accuracy"}]}}
        case = SimpleNamespace(status="draft", project_product_id=1, dataset_version_id=1, dataset_version=SimpleNamespace(), config=config)
        with patch.object(EvaluationCase.objects, "select_related") as query, patch("src.apps.evaluation.services.case.ensure_product_scope"), patch.object(EvaluationCaseService, "normalize", return_value={"config": config}), patch.object(EvaluationCaseService, "ensure_target_access"), patch.object(EvaluationCaseService, "selected_items", return_value=[SimpleNamespace()]), patch("src.apps.evaluation.services.case.EvaluationTargetAdapterRegistry.get") as adapter:
            query.return_value.filter.return_value.first.return_value = case
            self.assertEqual(EvaluationCaseService.validate(1, SimpleNamespace(id=1)), {"valid": True, "item_count": 1})
            adapter.return_value.execute.assert_not_called()
