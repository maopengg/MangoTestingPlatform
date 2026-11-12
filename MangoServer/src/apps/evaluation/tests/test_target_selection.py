from src.apps.user.services.authorization.http_permission_registry import permission_for_view
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.urls import resolve

from src.apps.evaluation.enums import EvaluationTargetTypeEnum
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.schemas import EvaluationTargetBinding
from src.apps.evaluation.selectors.target import interface_choices, published_interfaces
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.services.targets.python_target import run_python_target
from src.apps.evaluation.services.targets.adapters import PythonTargetAdapter


class TargetSelectionTests(SimpleTestCase):
    def test_catalog_exposes_only_interface_and_python(self):
        self.assertEqual(EvaluationTargetTypeEnum.get_option(), [
            {"key": "api_info", "title": "接口管理"}, {"key": "script", "title": "Python 脚本"},
        ])

    def test_interface_options_have_explicit_case_permission_mapping(self):
        match = resolve("/api/evaluation/case/1/interfaces")
        view = match.func.cls
        self.assertEqual(match.func.actions, {"get": "interfaces"})
        self.assertEqual(permission_for_view(view, "interfaces"), ("evaluation.case:read", "evaluation.case:change"))

    def test_source_queryset_is_product_and_protocol_limited(self):
        with patch("src.apps.evaluation.selectors.target.ApiQuerySelector") as source:
            published_interfaces(8)
            source.api_info.return_value.filter.assert_called_once_with(project_product_id=8, protocol_type__in=["http", "sse", "mcp"])
            source.current_published_info_releases.assert_called_once()

    def test_selector_requires_interface_execute_permission(self):
        with patch("src.apps.evaluation.selectors.target.get_case", return_value=SimpleNamespace(project_product_id=8)), \
                patch("src.apps.evaluation.selectors.target.PermissionMenuService.is_effective_super_admin", return_value=False), \
                patch("src.apps.evaluation.selectors.target.PermissionMenuService.permission_keys_for_user", return_value={"evaluation.case:read"}), \
                patch("src.apps.evaluation.selectors.target.published_interfaces") as query:
            with self.assertRaises(EvaluationError):
                interface_choices(1, SimpleNamespace(), module_id=2)
            query.assert_not_called()

    def test_selector_marks_unpublished_and_limits_module(self):
        query = MagicMock()
        query.filter.return_value = query
        query.count.return_value = 2
        query.order_by.return_value.__getitem__.return_value = [
            SimpleNamespace(id=1, name="事件流", module_id=2, protocol_type="sse", published_release_id=9),
            SimpleNamespace(id=2, name="草稿", module_id=2, protocol_type="http", published_release_id=None),
        ]
        with patch("src.apps.evaluation.selectors.target.get_case", return_value=SimpleNamespace(project_product_id=8)), \
                patch("src.apps.evaluation.selectors.target.PermissionMenuService.is_effective_super_admin", return_value=True), \
                patch("src.apps.evaluation.selectors.target.published_interfaces", return_value=query):
            data = interface_choices(1, SimpleNamespace(), module_id=2, search="问答")
        query.filter.assert_any_call(module_id=2)
        query.filter.assert_any_call(name__icontains="问答")
        self.assertEqual([item["published"] for item in data["items"]], [True, False])
        self.assertNotIn("published_release_id", data["items"][0])

    def test_save_resolves_release_instead_of_trusting_client_version(self):
        raw = {"target": {"type": "api_info", "ref_id": 7, "version_ref": {"kind": "api_info_revision", "id": 999}}, "grading": {}}
        with patch("src.apps.evaluation.services.assets.case.validate_relation", side_effect=lambda values, _: values), \
                patch("src.apps.evaluation.selectors.target.published_interfaces") as query:
            query.return_value.filter.return_value.first.return_value = SimpleNamespace(published_release_id=42)
            values = EvaluationCaseService.normalize({"project_product": SimpleNamespace(id=8), "config": raw})
        self.assertEqual(values["config"]["target"]["version_ref"], {"kind": "api_info_release", "id": 42})
        self.assertEqual(raw["target"]["version_ref"]["id"], 999)

    def test_unpublished_and_other_product_interface_cannot_be_saved(self):
        for interface in (None, SimpleNamespace(published_release_id=None)):
            with patch("src.apps.evaluation.services.assets.case.validate_relation", side_effect=lambda values, _: values), \
                    patch("src.apps.evaluation.selectors.target.published_interfaces") as query:
                query.return_value.filter.return_value.first.return_value = interface
                with self.assertRaises(EvaluationError):
                    EvaluationCaseService.normalize({"project_product": SimpleNamespace(id=8), "config": {"target": {"type": "api_info", "ref_id": 7}, "grading": {}}})

    def test_python_runs_with_visible_input_and_context(self):
        result = run_python_target('def main(input, context):\n    print("diagnostic")\n    return {"answer": input["question"], "evidence": context["text"]}',
                                   {"question": "姓名"}, {"text": "Alice"}, 5)
        self.assertEqual(result, {"answer": "姓名", "evidence": "Alice"})

    def test_python_failure_timeout_and_non_object_are_invalid(self):
        for code, timeout in [
            ('def main(input, context):\n    return [1]', 5),
            ('def main(input, context):\n    raise RuntimeError("private detail")', 5),
            ('def main(input, context):\n    while True: pass', 0.05),
            ('not python', 5),
        ]:
            with self.subTest(code=code), self.assertRaises(EvaluationError) as caught:
                run_python_target(code, {}, {}, timeout)
            self.assertNotIn("private detail", str(caught.exception))

    def test_python_adapter_never_exposes_expected_or_hidden_context(self):
        item = SimpleNamespace(input_data={"query": "问题"}, context={"target_visible": {"allowed": True}, "hidden": "secret"}, metadata={}, expected_output={"answer": "gold"})
        with patch("src.apps.evaluation.services.targets.python_target.run_python_target", return_value={"answer": "result"}) as run:
            PythonTargetAdapter.execute(target=SimpleNamespace(executor_config={"code": "code"}), dataset_item=item,
                mapping=SimpleNamespace(input_variable="case_input", output_mapping={"paths": []}), execution=None, user_id=1)
        self.assertEqual(run.call_args.args[1:3], ({"case_input": {"query": "问题"}}, {"allowed": True}))

    def test_python_contract_needs_no_business_id_or_version(self):
        parsed = EvaluationTargetBinding.model_validate({"type": "script", "parameters": {"code": "def main(input, context): return input"}})
        self.assertIsNone(parsed.ref_id)
        self.assertIsNone(parsed.version_ref)
