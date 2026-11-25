from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import InterfaceError
from django.db.models import Q
from django.test import SimpleTestCase

from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
from src.interfaces.mcp.tools.data_factory import helpers
from src.interfaces.mcp.tools.data_factory.execution import register_execution_tools


class ExecutionDetailReadTests(SimpleTestCase):
    def test_factory_audit_uses_indexed_ids_and_loads_heavy_payload_without_sort(self):
        path = 'src.apps.data_factory.selectors.execution_audit'
        with patch(path + '.SqlExecutionRecord') as records, \
                patch('src.apps.data_factory.models.DataFactoryExecutionItem') as items:
            items.objects.filter.return_value.values_list.return_value = [11, 12]
            filtered, payloads = Mock(), Mock()
            records.objects.filter.side_effect = [filtered, payloads]
            filtered.order_by.return_value.values_list.return_value = [102, 101]
            first, second = SimpleNamespace(id=102), SimpleNamespace(id=101)
            payloads.order_by.return_value.in_bulk.return_value = {101: second, 102: first}
            self.assertEqual(ExecutionAuditSelector.factory_records(7), [first, second])
            args, kwargs = records.objects.filter.call_args_list[0]
            self.assertEqual(args, (Q(source_id__in=[7, 11, 12]) | Q(source_id__isnull=True),))
            self.assertEqual(kwargs, {'source_type': 'data_factory', 'source_detail__execution_id': 7})
            filtered.order_by.return_value.values_list.assert_called_once_with('id', flat=True)
            payloads.order_by.assert_called_once_with()

    def test_detail_retries_only_read_and_returns_complete_second_result(self):
        path = 'src.common.database.read_retry'
        connection = SimpleNamespace(in_atomic_block=False, close=Mock())
        value = {'execution': {'id': 7}, 'items': [], 'sql_executions': []}
        with patch.object(helpers, '_read_execution_detail', side_effect=[InterfaceError(0, ''), value]) as read, \
                patch(path + '.connections', {'default': connection}):
            self.assertIs(helpers._execution_detail(7), value)
        self.assertEqual(read.call_count, 2)
        connection.close.assert_called_once()

    def registered_tools(self):
        tools = {}
        def register(function):
            tools[function.__name__] = function
            return function
        registry = SimpleNamespace(tool=lambda *args, **kwargs: register)
        register_execution_tools(registry)
        return tools

    def test_cleanup_preview_does_not_replay_confirmation_or_cleanup(self):
        tools = self.registered_tools()
        connection = SimpleNamespace(in_atomic_block=False, close=Mock())
        value = {'execution': {'id': 7, 'execution_no': 'example'}, 'items': []}
        path = 'src.interfaces.mcp.tools.data_factory.execution'
        with patch.object(helpers, '_read_execution_detail', side_effect=[InterfaceError(0, ''), value]) as read, \
                patch('src.common.database.read_retry.connections', {'default': connection}), \
                patch(path + '.create_dangerous_action_preview', return_value={}) as confirmation, \
                patch(path + '.DataFactoryCleanup.cleanup_execution') as cleanup:
            tools['preview_cleanup_data_factory_execution_impact'](7)
            self.assertEqual(read.call_count, 2)
            confirmation.assert_called_once()
            cleanup.assert_not_called()

    def test_preview_failure_does_not_create_confirmation_or_cleanup(self):
        tools = self.registered_tools()
        connection = SimpleNamespace(in_atomic_block=False, close=Mock())
        path = 'src.interfaces.mcp.tools.data_factory.execution'
        with patch.object(helpers, '_read_execution_detail', side_effect=InterfaceError(0, '')), \
                patch('src.common.database.read_retry.connections', {'default': connection}), \
                patch(path + '.create_dangerous_action_preview') as confirmation, \
                patch(path + '.DataFactoryCleanup.cleanup_execution') as cleanup, self.assertRaises(InterfaceError):
            tools['preview_cleanup_data_factory_execution_impact'](7)
        confirmation.assert_not_called()
        cleanup.assert_not_called()
