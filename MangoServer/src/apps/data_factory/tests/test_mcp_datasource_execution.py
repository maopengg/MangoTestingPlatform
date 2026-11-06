from unittest.mock import patch
from types import SimpleNamespace

from django.test import SimpleTestCase

from src.interfaces.mcp.tools.data_factory.datasource import register_datasource_tools
from src.interfaces.mcp.tools.data_factory.schema import register_schema_tools
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.data_source_execution_request import DataSourceExecutionRequestService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


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
        actor = patch('src.interfaces.mcp.tools.data_factory.datasource.mcp_current_user_id', return_value=4)
        actor.start()
        self.addCleanup(actor.stop)
        self.mcp = FakeMcp()
        register_datasource_tools(self.mcp)

    def test_sql_query_is_not_registered(self):
        self.assertNotIn('query_data_factory_datasource_sql', self.mcp.tools)
        register_schema_tools(self.mcp)
        workflow = self.mcp.tools['get_data_factory_schema']()['data']['entity_field_rule_workflow']
        self.assertNotIn('query_sql', workflow['tools'])

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
            expected_db_type=DataSourceTypeEnum.REDIS.value,
            source_context={'source_type': 'mcp', 'source_stage': 'query', 'source_id': 9,
                            'mcp_tool_name': 'query_data_factory_datasource_redis', 'operator_id': 4},
        )

    def test_other_query_tools_cannot_be_used_as_sql_entry_points(self):
        for db_type in [DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value,
                        DataSourceTypeEnum.SQLITE.value]:
            binding = SimpleNamespace(database=SimpleNamespace(db_type=db_type))
            with (
                self.subTest(db_type=db_type),
                patch('src.apps.data_factory.services.data_source_execution_request.'
                      'DataFactoryDatasourceResolver.resolve_binding_by_env', return_value=binding),
                patch('src.apps.data_factory.services.data_source_execution_request.'
                      'DataSourceExecutionService.execute') as execute,
            ):
                with self.assertRaises(DataFactoryError):
                    self.mcp.tools['query_data_factory_datasource_redis']('SELECT 1', 9, 22, 1)
                with self.assertRaises(DataFactoryError):
                    self.mcp.tools['query_data_factory_datasource_elasticsearch']('records', {}, 9, 22, 1)
                execute.assert_not_called()

    def test_typed_query_still_checks_write_confirmation(self):
        binding = SimpleNamespace(database=SimpleNamespace(db_type=DataSourceTypeEnum.REDIS.value))
        with (
            patch('src.apps.data_factory.services.data_source_execution_request.'
                  'DataFactoryDatasourceResolver.resolve_binding_by_env', return_value=binding),
            patch('src.apps.data_factory.services.data_source_execution_request.'
                  'DataSourceExecutionService.is_write_operation', return_value=True),
            patch('src.apps.data_factory.services.data_source_execution_request.'
                  'DataSourceExecutionService.execute') as execute,
        ):
            with self.assertRaises(DataFactoryError):
                DataSourceExecutionRequestService.execute_operation(
                    datasource_alias_id=9, project_product_id=22, test_env=1,
                    operation_config='SET key value', expected_db_type=DataSourceTypeEnum.REDIS.value,
                )
            execute.assert_not_called()

    def test_platform_sql_execution_remains_available(self):
        binding = SimpleNamespace(database=SimpleNamespace(db_type=DataSourceTypeEnum.MYSQL.value))
        with (
            patch('src.apps.data_factory.services.data_source_execution_request.'
                  'DataFactoryDatasourceResolver.resolve_binding_by_env', return_value=binding),
            patch('src.apps.data_factory.services.data_source_execution_request.'
                  'DataSourceExecutionService.is_write_operation', return_value=False),
            patch('src.apps.data_factory.services.data_source_execution_request.'
                  'DataSourceExecutionService.execute', return_value={'rows': []}) as execute,
        ):
            result = DataSourceExecutionRequestService.execute_operation(
                datasource_alias_id=9, project_product_id=22, test_env=1, operation_config='SELECT 1',
            )
        self.assertEqual(result['rows'], [])
        execute.assert_called_once()
