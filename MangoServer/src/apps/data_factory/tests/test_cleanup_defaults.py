import inspect
from typing import get_args, get_type_hints
from unittest.mock import Mock

from django.test import SimpleTestCase

from src.apps.data_factory.models import DataFactoryCaseConfig, DataFactoryTemplate
from src.interfaces.mcp.tools.data_factory.case_config import register_case_config_tools
from src.interfaces.mcp.tools.data_factory.template import register_template_tools


class CleanupDefaultTests(SimpleTestCase):
    def tools(self):
        registered = {}

        def register(function):
            registered[function.__name__] = function
            return function

        mcp = Mock()
        mcp.tool.return_value = register
        register_template_tools(mcp)
        register_case_config_tools(mcp)
        return registered

    def test_models_default_to_execution_end(self):
        self.assertEqual(DataFactoryTemplate().cleanup_strategy, 1)
        self.assertEqual(DataFactoryCaseConfig().cleanup_strategy, 1)

    def test_explicit_manual_and_inherited_settings_are_preserved(self):
        self.assertEqual(DataFactoryTemplate(cleanup_strategy=2).cleanup_strategy, 2)
        self.assertEqual(DataFactoryCaseConfig(cleanup_strategy=3).cleanup_strategy, 3)
        self.assertIsNone(DataFactoryCaseConfig(cleanup_strategy=None).cleanup_strategy)

    def test_mcp_creation_defaults_and_enums(self):
        tools = self.tools()
        for name in ('create_data_factory_template', 'bind_data_factory_to_case_source'):
            function = tools[name]
            self.assertEqual(inspect.signature(function).parameters['cleanup_strategy'].default, 1)
            annotation = get_type_hints(function)['cleanup_strategy']
            values = get_args(annotation)
            if type(None) in values:
                values = get_args(values[0])
            self.assertEqual(values, (1, 2, 3))
            self.assertIn('用户未明确要求保留数据', function.__doc__)

    def test_updates_do_not_silently_change_existing_strategy(self):
        tools = self.tools()
        for name in ('update_data_factory_template', 'update_data_factory_case_config'):
            function = tools[name]
            self.assertIsNone(inspect.signature(function).parameters['cleanup_strategy'].default)
            self.assertIn('不修改', function.__doc__)
