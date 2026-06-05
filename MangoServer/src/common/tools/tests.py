import json

from django.test import SimpleTestCase
from mangotools.exceptions import MangoToolsError

from src.common.tools.obtain_assertion import ObtainAssertion
from src.common.tools.obtain_test_data import ObtainTestData


class ObtainTestDataReplacementTests(SimpleTestCase):

    def test_replace_allows_cached_none_and_empty_string_values(self):
        test_data = ObtainTestData()
        test_data.set_cache("empty_value", "")
        test_data.set_cache("null_value", None)

        self.assertEqual(test_data.replace("${{empty_value}}"), "")
        self.assertEqual(test_data.replace("${{null_value}}"), "")

    def test_replace_still_rejects_missing_cache_key(self):
        test_data = ObtainTestData()

        with self.assertRaises(MangoToolsError):
            test_data.replace("${{missing_value}}")

    def test_replace_supports_cache_placeholders_in_dict_keys(self):
        test_data = ObtainTestData()
        test_data.set_cache("query_key", "user_id_type")

        self.assertEqual(
            test_data.replace({"${{query_key}}": "user_id"}),
            {"user_id_type": "user_id"},
        )

    def test_replace_preserves_list_when_placeholder_is_entire_value(self):
        test_data = ObtainTestData()
        test_data.set_cache("user_ids", ["dg8689b9"])

        self.assertEqual(test_data.replace("${{user_ids}}"), ["dg8689b9"])

    def test_replace_keeps_json_placeholder_values_as_json_types(self):
        test_data = ObtainTestData()
        test_data.set_cache("contract_id", 1071830070739337582)
        test_data.set_cache("user_ids", ["dg8689b9"])

        replaced = test_data.replace('{"contract_id": "${{contract_id}}", "user_ids": "${{user_ids}}"}')

        self.assertEqual(json.loads(replaced), {
            "contract_id": 1071830070739337582,
            "user_ids": ["dg8689b9"],
        })


class ObtainAssertionTests(SimpleTestCase):

    def test_equal_assertion_accepts_same_numeric_values_with_different_runtime_types(self):
        result = ObtainAssertion().ass("p_is_equal_to", actual=110000, expect=110000)

        self.assertEqual(result, "实际=110000, 预期=110000")

    def test_equal_assertion_accepts_same_boolean_values_with_different_runtime_types(self):
        result = ObtainAssertion().ass("p_is_equal_to", actual=False, expect=False)

        self.assertEqual(result, "实际=False, 预期=False")
