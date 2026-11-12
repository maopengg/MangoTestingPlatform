import json
import re
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.exceptions import MangoToolsError

from src.common.testing import ObtainTestData
from src.interfaces.mcp.tools.api.schema import register_schema_tools
from src.interfaces.mcp.tools.system.variable import register_system_variable_tools


def registered_tools(register):
    result = {}

    def tool():
        def decorate(function):
            result[function.__name__] = function
            return function
        return decorate

    register(SimpleNamespace(tool=tool))
    return result


class VariableMethodExampleTests(SimpleTestCase):
    def test_random_method_is_discoverable_and_catalog_example_runs(self):
        tools = registered_tools(register_system_variable_tools)
        result = tools['list_test_data_methods'](keyword='str_random_string')
        methods = [method for group in result['data']['items']
                   for category in group['children'] for method in category['children']]
        method = next(item for item in methods if item['value'] == 'str_random_string')
        value = ObtainTestData().replace(method['example'])
        self.assertIsInstance(value, str)
        self.assertTrue(value.isalnum())

    def test_evaluation_prompt_contains_a_runnable_method(self):
        tools = registered_tools(register_system_variable_tools)
        failure = tools['evaluate_test_data_expression']('field_name')
        self.assertEqual(failure['error_code'], 'INVALID_TEST_DATA_EXPRESSION')
        expression = re.search(r'\$\{\{[^{}]+\}\}', failure['message']).group()
        success = tools['evaluate_test_data_expression'](expression)
        self.assertTrue(success['success'])
        self.assertEqual(len(success['data']['value']), 8)

    @patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names', return_value={})
    def test_api_schema_random_examples_use_registered_methods(self, _):
        schema = registered_tools(register_schema_tools)['get_api_case_schema']()
        text = json.dumps(schema, ensure_ascii=False)
        expressions = re.findall(r'\$\{\{str_random_string\(\d+\)\}\}', text)
        self.assertGreaterEqual(len(expressions), 2)
        self.assertNotRegex(text, r'(?<!\w)(?:random_str|random_string)\(')
        for expression in expressions:
            length = int(re.search(r'\((\d+)\)', expression).group(1))
            self.assertEqual(len(ObtainTestData().replace(expression)), length)
        self.assertIn('list_test_data_methods', text)
        self.assertIn('evaluate_test_data_expression', text)

    def test_generated_name_can_be_reused_by_request_and_cleanup(self):
        data = ObtainTestData()
        name = data.replace('${{str_random_string(24)|field_name}}')
        self.assertEqual(len(name), 24)
        self.assertEqual(data.replace('${{field_name}}'), name)
        self.assertEqual(data.replace('WHERE name=\'${{field_name}}\''), f"WHERE name='{name}'")

    def test_unknown_method_is_not_silently_replaced_by_another_generator(self):
        with self.assertRaises(MangoToolsError) as caught:
            ObtainTestData().replace('${{random_str(24)}}')
        self.assertEqual(caught.exception.code, 3047)
