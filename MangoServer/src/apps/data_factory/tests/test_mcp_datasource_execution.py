from unittest.mock import patch

from django.test import SimpleTestCase

from src.interfaces.mcp.tools.data_factory.datasource import register_datasource_tools


class FakeMcp:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


class McpDatasourceExecutionTests(SimpleTestCase):

    def setUp(self):
        self.mcp = FakeMcp()
        register_datasource_tools(self.mcp)

    @patch(
        'src.interfaces.mcp.tools.data_factory.datasource.'
        'DataSourceExecutionRequestService.execute_operation'
    )
    def test_sql_query_uses_unified_execution_request(self, execute_operation):
        execute_operation.return_value = {
            'rows': [{'id': 1}, {'id': 2}],
            'result': [{'id': 1}, {'id': 2}],
            'row_count': 2,
        }

        response = self.mcp.tools['query_data_factory_datasource_sql'](
            'SELECT id FROM users',
            9,
            22,
            1,
            limit=1,
        )

        execute_operation.assert_called_once_with(
            datasource_alias_id=9,
            project_product_id=22,
            test_env=1,
            operation_config='SELECT id FROM users',
            confirm_write=False,
            source_context={
                'source_type': 'mcp',
                'source_stage': 'query',
                'source_id': 9,
                'mcp_tool_name': 'query_data_factory_datasource_sql',
            },
        )
        self.assertEqual(response['data']['rows'], [{'id': 1}])

    @patch(
        'src.interfaces.mcp.tools.data_factory.datasource.'
        'DataSourceExecutionRequestService.execute_operation'
    )
    def test_redis_query_uses_unified_execution_request(self, execute_operation):
        execute_operation.return_value = {'result': 'value'}

        self.mcp.tools['query_data_factory_datasource_redis']('GET user:1', 9, 22, 1)

        execute_operation.assert_called_once_with(
            datasource_alias_id=9,
            project_product_id=22,
            test_env=1,
            operation_config='GET user:1',
            confirm_write=False,
        )
