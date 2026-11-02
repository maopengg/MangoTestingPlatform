from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.evaluation.api.views.dataset import DatasetCRUD
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.services.graders import JsonSchemaGrader, ExactMatchGrader, SetMatchGrader
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService


class EvaluationCompletionTests(SimpleTestCase):
    def test_file_import_routes_and_tools_are_removed(self):
        from src.apps.evaluation.api.urls import urlpatterns
        from src.apps.evaluation.api.views.dataset_version import DatasetVersionViews
        from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
        self.assertFalse(any("import-preview" in str(route.pattern) or "import-confirm" in str(route.pattern) for route in urlpatterns))
        self.assertFalse(hasattr(DatasetVersionViews, "import_preview"))
        self.assertFalse(hasattr(DatasetVersionViews, "import_confirm"))
        self.assertNotIn("preview_import_evaluation_dataset_items", MCP_PERMISSION_RULES)
        self.assertNotIn("import_evaluation_dataset_items", MCP_PERMISSION_RULES)

    def test_missing_gold_path_cannot_match_another_missing_path(self):
        with self.assertRaises(EvaluationError):
            ExactMatchGrader.evaluate(dataset_item={"expected_output": {"answer": 1}}, actual={},
                                     config={"expected_path": "missing", "actual_path": "missing"}, metric_key="answer", threshold=100)

    def test_missing_actual_field_is_different_from_explicit_null(self):
        for actual, passed in (({}, False), ({"answer": None}, True)):
            with self.subTest(actual=actual):
                result = ExactMatchGrader.evaluate(dataset_item={"expected_output": {"answer": None}}, actual=actual,
                    config={"expected_path": "answer", "actual_path": "answer"}, metric_key="answer", threshold=100)
                self.assertEqual(result.metrics[0].passed, passed)

    def test_missing_collection_is_not_a_correct_empty_collection(self):
        for actual in ({}, {"ids": None}, {"ids": {}}):
            result = SetMatchGrader.evaluate(dataset_item={"expected_output": {"ids": []}}, actual=actual,
                config={"expected_path": "ids", "actual_path": "ids"}, metric_key="recall", threshold=100)
            self.assertFalse(result.metrics[0].passed)

    def test_json_schema_uses_the_selected_gold_schema(self):
        for value, passed in (("not-an-integer", False), (5, True)):
            with self.subTest(value=value):
                result = JsonSchemaGrader.evaluate(
                    dataset_item={"expected_output": {"answer_schema": {"type": "integer"}}},
                    actual={"answer": value},
                    config={"expected_path": "answer_schema", "actual_path": "answer"},
                    metric_key="shape", threshold=100,
                )
                self.assertEqual(result.metrics[0].passed, passed)
                self.assertEqual(result.metrics[0].score, 100 if passed else 0)

    def test_missing_or_malformed_schema_is_configuration_failure(self):
        for expected in ({}, {"schema": {"type": "unknown-type"}}):
            with self.subTest(expected=expected), self.assertRaises(EvaluationError):
                JsonSchemaGrader.evaluate(dataset_item={"expected_output": expected}, actual={"answer": 1},
                                         config={"expected_path": "schema"}, metric_key="shape", threshold=100)

    def test_explicit_empty_schema_is_not_replaced_by_expected_output(self):
        result = JsonSchemaGrader.evaluate(dataset_item={"expected_output": {"type": "integer"}}, actual={"answer": "value"},
                                          config={"schema": {}, "actual_path": "answer"}, metric_key="shape", threshold=100)
        self.assertTrue(result.metrics[0].passed)


    def test_dataset_status_and_content_share_change_permission(self):
        for data, grants, allowed in (
            ({"id": 1, "status": "archived"}, {"evaluation.dataset:change"}, True),
            ({"id": 1, "status": "archived"}, {"evaluation.dataset:read"}, False),
            ({"id": 1, "status": "archived", "name": "new"}, {"evaluation.dataset:read"}, False),
            ({"id": 1, "status": "archived", "name": "new"}, {"evaluation.dataset:change"}, True),
        ):
            request = SimpleNamespace(method="PUT", path="/api/evaluation/dataset", data=data, query_params={}, user=SimpleNamespace(user_obj=SimpleNamespace(id=1)))
            with self.subTest(data=data, grants=grants), patch.object(PermissionMenuService, "is_effective_super_admin", return_value=False), patch.object(PermissionMenuService, "permission_keys_for_user", return_value=grants):
                self.assertEqual(MenuActionPermission().has_permission(request, DatasetCRUD()), allowed)
