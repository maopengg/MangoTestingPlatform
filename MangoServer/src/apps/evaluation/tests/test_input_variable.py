from django.test import SimpleTestCase
from pydantic import ValidationError
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.schemas.case import EvaluationDataSelection, EvaluationCaseConfig
from src.apps.evaluation.services.targets.python_target import run_python_target
from src.apps.evaluation.schemas.item import EvaluationDatasetItemPayload
from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService
from types import SimpleNamespace


class InputVariableTests(SimpleTestCase):
    def test_dataset_inputs_accept_json_values_and_still_follow_the_published_schema(self):
        for value in ("question", ["a", 0], False, 0, {"query": "question", "optional": None}):
            row = EvaluationDatasetItemPayload(input_data=value).model_dump(mode="json")
            EvaluationVersionService.validate_item(SimpleNamespace(schema_snapshot={}), row)
            self.assertEqual(row["input_data"], value)
        with self.assertRaises(EvaluationError):
            EvaluationVersionService.validate_item(SimpleNamespace(schema_snapshot={"input_schema": {"type": "string"}}),
                EvaluationDatasetItemPayload(input_data={"query": "question"}).model_dump(mode="json"))

    def test_python_bare_and_quoted_values_cannot_inject_code(self):
        code = '''def main(input, context):
    bare = ${{payload}}
    quoted = "${{payload}}"
    embedded = "prefix:${{payload}}"
    formatted = f"value:${{payload}}"
    return {"bare": bare, "quoted": quoted, "embedded": embedded, "formatted": formatted}
'''
        for value in ({"query": "问题", "flag": False}, "'\"\n\\中文 __import__('os')", [0, False, None]):
            with self.subTest(value=value):
                output = run_python_target(code, {"payload": value}, {}, 5)
                self.assertEqual(output["bare"], value)
                self.assertEqual(output["quoted"], value)
                self.assertEqual(output["embedded"], "prefix:" + str(value))
                self.assertEqual(output["formatted"], "value:" + str(value))
        with self.assertRaises(EvaluationError):
            run_python_target('def main(input, context): return {"answer": ${{unknown}}}', {"payload": "question"}, {}, 5)

    def test_variable_validation_and_removed_preparation_cleanup(self):
        for name in ("", "bad.name", "1name", "two words"):
            with self.subTest(name=name), self.assertRaises(ValidationError):
                EvaluationDataSelection(input_variable=name)
        from src.apps.evaluation.tests.test_case_flow import case_config
        old = {**case_config(), "runtime_context": [{"key": "old"}], "mapping": {"input": {"mode": "template", "template": {"old": 1}}, "output": {"mode": "identity"}}}
        value = EvaluationCaseConfig.model_validate(old).model_dump(mode="json")
        self.assertNotIn("runtime_context", value)
        self.assertNotIn("input", value["mapping"])
        self.assertNotIn("input_variable", value["data_selection"])

    def test_saved_aliases_and_grader_paths_are_removed_together(self):
        from src.apps.evaluation.tests.test_case_flow import case_config
        config = case_config()
        config["mapping"] = {"output": {"mode": "jsonpath", "selectors": {"answer": "$.json.answer"}}}
        config["grading"]["default_graders"][0]["parameters"] = {"actual_path": "answer", "expected_path": "answer"}
        config["answering"] = {"memories_path": "answer"}
        result = EvaluationCaseConfig.model_validate(config).model_dump(mode="json")
        self.assertEqual(result["mapping"]["output"], {"paths": ["$.json.answer"]})
        self.assertEqual(result["grading"]["default_graders"][0]["parameters"], {"actual_path": "", "expected_path": "answer"})
        self.assertNotIn("memories_path", result["answering"])
        self.assertIn("selectors", config["mapping"]["output"], "Validation must not mutate the saved record")

    def test_saved_collection_paths_become_ordered_values(self):
        from src.apps.evaluation.tests.test_case_flow import case_config
        config = case_config()
        config["mapping"] = {"output": {"mode": "select", "selectors": {"first": "json.items.0.content"},
            "collections": {"all": {"path": "json.items", "value_path": "$", "cardinality": "many"}}}}
        config["grading"]["default_graders"][0]["parameters"] = {"actual_path": "all.0.content"}
        result = EvaluationCaseConfig.model_validate(config).model_dump(mode="json")
        self.assertEqual(result["mapping"]["output"]["paths"], ["$.json.items[0].content", "$.json.items"])
        self.assertEqual(result["grading"]["default_graders"][0]["parameters"]["actual_path"], "1.0.content")
