from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
from pydantic import ValidationError
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.formatters.payload import apply_mapping
from src.apps.evaluation.schemas.mapping import EvaluationMapping
from src.apps.evaluation.services.target_input import compile_target_input
from src.apps.evaluation.services.adapters import ApiInfoTargetAdapter
from src.common.testing import ObtainTestData


class SimpleExtractionTests(SimpleTestCase):
    @staticmethod
    def item(data):
        return SimpleNamespace(input_data=data, context={"target_visible": {"allowed": True}, "hidden": "private"},
            expected_output={"answer": "gold"}, metadata={})

    def test_complete_input_preserves_types_and_is_copied(self):
        for data in ({"query": "question", "nested": [False, None, 0]}, ["question", 0], "question", False, 0, ""):
            with self.subTest(data=data):
                cache = ObtainTestData()
                parameters = compile_target_input(self.item(data), "payload")
                self.assertEqual(parameters, {"payload": data})
                cache.set_cache("payload", parameters["payload"])
                self.assertEqual(cache.replace({"body": "${{payload}}"}), {"body": data})
        original = {"items": [1]}
        result = compile_target_input(self.item(original))
        result["case_input"]["items"].append(2)
        self.assertEqual(original, {"items": [1]})

    def test_interface_runner_receives_explicit_runtime_variables(self):
        runtime = MagicMock()
        runtime.test_setup.test_data = ObtainTestData()
        runtime.api_info_run.return_value = {"code": 200, "json": {"data": {"answer": "北京"}}}
        with patch.object(ApiInfoTargetAdapter, 'validate_target'), patch('src.apps.evaluation.services.adapters.TestApiInfo', return_value=runtime):
            result = ApiInfoTargetAdapter.execute(target=SimpleNamespace(target_ref_id=7, executor_config={"revision_id": 2}),
                dataset_item=self.item({"messages": [{"content": "问题"}], "top_k": 5}),
                mapping=SimpleNamespace(input_variable="case_input",
                    output_mapping={"paths": ["$.json.data.answer"]}),
                execution=SimpleNamespace(test_env=1), user_id=1)
        self.assertEqual(result["output"], "北京")
        runtime.api_info_run.assert_called_once_with(7, revision_id=2, release_id=None,
            runtime_parameters={'case_input': {'messages': [{'content': '问题'}], 'top_k': 5}})

    def test_response_extraction_handles_arrays_null_false_and_zero(self):
        raw = {"json": {"answer": "北京", "items": [{"id": 1}, {"id": 2}], "empty": [], "none": None, "flag": False, "count": 0}}
        result = apply_mapping(raw, {"paths": ["$.json.answer", "$.json.items[*].id", "$.json.empty", "$.json.none", "$.json.flag", "$.json.count"]})
        self.assertEqual(result, ["北京", [1, 2], [], None, False, 0])
        for key in ("empty", "none", "flag", "count"):
            self.assertEqual(apply_mapping(raw, {"paths": [f"$.json.{key}"]}), raw["json"][key])

    def test_empty_extraction_keeps_full_response(self):
        raw = {"json": {"answer": "北京"}}
        self.assertEqual(apply_mapping(raw, {"paths": []}), raw)

    def test_missing_or_malformed_path_is_a_business_error(self):
        for path in ("$.missing", "$.items[", "$.items[4]"):
            with self.subTest(path=path), self.assertRaises(EvaluationError):
                apply_mapping({"items": []}, {"paths": [path]})

    def test_binding_does_not_read_gold_or_hidden_context(self):
        self.assertEqual(compile_target_input(self.item({"query": "question"})), {"case_input": {"query": "question"}})

    def test_bindings_are_isolated_between_items(self):
        caches = [ObtainTestData(), ObtainTestData()]
        for cache, data in zip(caches, ("first", "second")):
            for key, value in compile_target_input(self.item(data)).items():
                cache.set_cache(key, value)
        self.assertEqual(caches[0].replace("${{case_input}}"), "first")
        self.assertEqual(caches[1].replace("${{case_input}}"), "second")

    def test_simple_schema_rejects_ambiguous_or_empty_expressions(self):
        for patch in ({"paths": [""]}, {"paths": ["x"]}, {"paths": ["$.x", "$.x"]},
                      {"template": {"x": 1}}, {"collections": {"items": {"path": "$.items"}}}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                EvaluationMapping.model_validate(patch)
