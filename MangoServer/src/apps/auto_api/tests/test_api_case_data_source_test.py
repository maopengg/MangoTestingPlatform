from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy.exc import IntegrityError, ProgrammingError

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.case_schema import validate_data_source_operation_list
from src.apps.auto_api.services.execution.base.api_base_test_setup.public_base import PublicBase
from src.apps.auto_api.services.execution.base.case_base import CaseBase
from src.apps.auto_api.services.execution.base.data_source_operation import execute_data_source_assertion, execute_data_source_operation
from src.apps.data_factory.services.datasource.data_source_execution import DataSourceExecutionService
from src.apps.data_factory.services.datasource.data_source_execution_request import DataSourceExecutionRequestService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.common.exceptions import ErrorDefinition


class FakeResult:
    def __init__(self, rows=None, rowcount=0):
        self._rows = rows or []
        self.returns_rows = rows is not None
        self.rowcount = rowcount

    def keys(self):
        return list(self._rows[0]._mapping.keys()) if self._rows else []

    def fetchmany(self, size):
        return self._rows[:size]


class FakeConnection:
    def __init__(self, result):
        self.result = result

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def execute(self, _statement):
        return self.result


class FakeEngine:
    def __init__(self, result):
        self.connection = FakeConnection(result)
        self.connect_called = False
        self.begin_called = False
        self.disposed = False

    def connect(self):
        self.connect_called = True
        return self.connection

    def begin(self):
        self.begin_called = True
        return self.connection

    def dispose(self):
        self.disposed = True


class DataSourceExecutionServiceTests(SimpleTestCase):
    @patch(
        'src.apps.auto_api.services.execution.base.api_base_test_setup.public_base.'
        'DataSourceExecutionService.execute'
    )
    def test_custom_code_datasource_callable_uses_unified_service(self, execute):
        execute.return_value = {'affected_rows': 1}
        setup = PublicBase.__new__(PublicBase)
        setup.test_object = SimpleNamespace(project_product_id=22, environment=1)

        result = setup.execute_data_source(9, 'UPDATE users SET enabled = 1 WHERE id = 7')

        self.assertEqual(result, {'affected_rows': 1})
        execute.assert_called_once_with(
            datasource_alias_id=9,
            project_product_id=22,
            test_env=1,
            operation_config='UPDATE users SET enabled = 1 WHERE id = 7',
            source_context={
                'source_type': 'api_custom_code',
                'source_stage': 'custom_code',
                'api_info_id': None,
            },
        )

    @patch(
        'src.apps.auto_api.services.execution.base.api_base_test_setup.public_base.cache_data_source_result',
        return_value=True,
    )
    @patch(
        'src.apps.auto_api.services.execution.base.api_base_test_setup.public_base.execute_data_source_query',
        return_value={'rows': [{'token': 'abc'}]},
    )
    def test_api_sql_public_variable_uses_unified_query_service(self, execute, cache_result):
        setup = PublicBase.__new__(PublicBase)
        setup.test_data = SimpleNamespace()
        public_variable = SimpleNamespace(
            datasource_alias_id=12,
            datasource_alias=SimpleNamespace(
                project_product_id=22,
                status=1,
                db_type=DataSourceTypeEnum.MYSQL.value,
            ),
            project_product_id=22,
            key='token',
            value='SELECT token FROM session LIMIT 1',
        )

        setup._PublicBase__sql(public_variable, 1)

        execute.assert_called_once_with(
            setup,
            1,
            {
                'datasource_alias': 12,
                'value': 'SELECT token FROM session LIMIT 1',
            },
            write_error=(300, 'SQL全局变量仅允许执行查询语句，不允许增删改数据库数据'),
            operation_name='SQL全局变量查询语句',
            source_context={
                'source_type': 'api_global_variable',
                'source_stage': 'global_variable',
                'source_id': None,
                'global_variable_id': None,
                'api_info_id': None,
            },
        )
        cache_result.assert_called_once_with(setup, 'token', {'rows': [{'token': 'abc'}]})

    def test_sql_assertion_rejects_write_statement_before_execution(self):
        test_setup = SimpleNamespace(
            test_object=SimpleNamespace(project_product_id=22),
            test_data=SimpleNamespace(replace=lambda value: value),
        )

        with self.assertRaisesMessage(AutoApiError, 'SQL断言仅允许执行查询语句'):
            execute_data_source_assertion(test_setup, 0, {
                'datasource_alias': 12,
                'value': 'DELETE FROM users WHERE id=1',
            })

    @patch('src.apps.auto_api.services.execution.base.data_source_operation.DataSourceExecutionService.execute')
    def test_api_runtime_uses_generic_data_source_execution_service(self, execute: Mock):
        execute.return_value = {'result': []}
        test_setup = SimpleNamespace(
            test_object=SimpleNamespace(project_product_id=22),
            test_data=SimpleNamespace(replace=lambda value: value),
        )
        operation_config = {
            'index': 'orders-*',
            'query': {'query': {'match_all': {}}},
        }

        result = execute_data_source_operation(test_setup, 0, {
            'datasource_alias': 12,
            'value': operation_config,
        })

        self.assertEqual(result, {'result': []})
        execute.assert_called_once_with(
            datasource_alias_id=12,
            project_product_id=22,
            test_env=0,
            operation_config=operation_config,
            source_context={
                'source_type': 'api_runtime',
                'source_stage': 'database_operation',
            },
        )

    @patch('src.apps.auto_api.services.execution.base.data_source_operation.DataSourceExecutionService.execute')
    def test_api_runtime_can_use_explicit_case_project_product_scope(self, execute: Mock):
        execute.return_value = {'affected_rows': 1}
        test_setup = SimpleNamespace(
            test_object=SimpleNamespace(project_product_id=16),
            test_data=SimpleNamespace(replace=lambda value: value),
        )

        execute_data_source_operation(
            test_setup,
            0,
            {'datasource_alias': 14, 'value': 'DELETE FROM task WHERE id=1'},
            project_product_id=2,
        )

        execute.assert_called_once_with(
            datasource_alias_id=14,
            project_product_id=2,
            test_env=0,
            operation_config='DELETE FROM task WHERE id=1',
            source_context={
                'source_type': 'api_runtime',
                'source_stage': 'database_operation',
            },
        )

    @patch('src.apps.auto_api.services.execution.base.case_base.execute_data_source_operation')
    def test_case_posterior_uses_case_scope_and_reports_failed_item(self, execute: Mock):
        execute.side_effect = AutoApiError(
            ErrorDefinition(code=300, message='逻辑数据源未绑定当前测试环境')
        )
        test_setup = SimpleNamespace(
            test_object=SimpleNamespace(project_product_id=16),
            test_data=SimpleNamespace(replace=lambda value: value),
        )
        api_case = SimpleNamespace(id=3739, project_product_id=2)
        case_base = CaseBase(test_setup, api_case, test_env=0)
        sql_rows = [{
            'key': 'cleanup_review_item',
            'value': 'DELETE FROM task WHERE id=1',
            'datasource_alias': 14,
            'test_envs': [0],
        }]

        with self.assertRaisesMessage(
                AutoApiError,
                '用例后置SQL执行失败（第1项，key=cleanup_review_item，逻辑数据库ID=14，'
                '执行环境=0，项目产品ID=2）：逻辑数据源未绑定当前测试环境',
        ):
            case_base._CaseBase__posterior_sql(sql_rows)

        execute.assert_called_once_with(
            test_setup,
            0,
            sql_rows[0],
            project_product_id=2,
            source_context={
                'source_type': 'api_case',
                'source_stage': 'case_posterior',
                'source_id': 3739,
                'case_id': 3739,
                'operation_index': 1,
            },
        )

    @patch('src.apps.auto_api.services.execution.base.data_source_operation.DataSourceExecutionService.execute')
    def test_api_runtime_preserves_data_source_business_error(self, execute: Mock):
        execute.side_effect = AutoApiError(
            ErrorDefinition(code=300, message='MySQL SQL语法或数据库对象错误：syntax error')
        )
        test_setup = SimpleNamespace(
            test_object=SimpleNamespace(project_product_id=22),
            test_data=SimpleNamespace(replace=lambda value: value),
        )

        with self.assertRaisesMessage(AutoApiError, 'MySQL SQL语法或数据库对象错误：syntax error'):
            execute_data_source_operation(test_setup, 0, {
                'datasource_alias': 12,
                'value': 'SELECT FORM users',
            })

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_operation_config_type_is_validated_by_datasource_type(self, filter_aliases: Mock):
        filter_aliases.return_value = [SimpleNamespace(
            id=12,
            project_product_id=22,
            status=1,
            db_type=DataSourceTypeEnum.ELASTICSEARCH.value,
        )]
        rows = validate_data_source_operation_list([{
            'key': 'orders',
            'datasource_alias': 12,
            'test_envs': [0],
            'value': {
                'index': 'orders-*',
                'query': {'query': {'match_all': {}}},
            },
        }], '前置数据库操作', 22)
        self.assertIsInstance(rows[0]['value'], dict)

        with self.assertRaisesMessage(AutoApiError, '必须是JSON对象'):
            validate_data_source_operation_list([{
                'key': 'orders',
                'datasource_alias': 12,
                'test_envs': [0],
                'value': 'orders-*',
            }], '前置数据库操作', 22)

    def test_cte_query_and_write_are_classified_by_main_statement(self):
        self.assertFalse(
            DataSourceExecutionService.is_write_operation(
                DataSourceTypeEnum.MYSQL.value,
                'WITH rows AS (SELECT 1 AS id) SELECT * FROM rows',
            )
        )
        self.assertTrue(
            DataSourceExecutionService.is_write_operation(
                DataSourceTypeEnum.MYSQL.value,
                'WITH rows AS (SELECT 1 AS id) UPDATE users SET enabled = 1',
            )
        )

    @patch('src.apps.data_factory.services.datasource.data_source_execution.DataFactoryDatasource.create_engine')
    def test_sql_syntax_error_keeps_driver_reason(self, create_engine: Mock):
        create_engine.side_effect = ProgrammingError(
            'SELECT FORM users',
            {},
            Exception('syntax error near FORM'),
        )
        database = SimpleNamespace(
            db_type=DataSourceTypeEnum.POSTGRESQL.value,
            password='secret',
        )

        with self.assertRaises(AutoApiError) as error:
            DataSourceExecutionService.execute_sql(
                database,
                'SELECT FORM users',
                is_write=False,
            )

        self.assertIn('PostgreSQL SQL语法或数据库对象错误', str(error.exception))
        self.assertIn('syntax error near FORM', str(error.exception))

    @patch('src.apps.data_factory.services.datasource.data_source_execution.DataFactoryDatasource.create_engine')
    def test_sql_integrity_error_is_classified(self, create_engine: Mock):
        create_engine.side_effect = IntegrityError(
            'INSERT INTO users(id) VALUES (1)',
            {},
            Exception('duplicate key value violates unique constraint'),
        )
        database = SimpleNamespace(
            db_type=DataSourceTypeEnum.POSTGRESQL.value,
            password='secret',
        )

        with self.assertRaises(AutoApiError) as error:
            DataSourceExecutionService.execute_sql(
                database,
                'INSERT INTO users(id) VALUES (1)',
                is_write=True,
            )

        self.assertIn('SQL违反数据库约束', str(error.exception))
        self.assertIn('duplicate key value', str(error.exception))

    @patch('src.apps.data_factory.services.datasource.data_source_execution_request.DataSourceExecutionService.execute')
    @patch(
        'src.apps.data_factory.services.datasource.data_source_execution_request.DataFactoryDatasourceResolver.resolve_binding_by_env')
    def test_write_requires_explicit_confirmation(
            self,
            resolve_binding: Mock,
            execute: Mock,
    ):
        resolve_binding.return_value = SimpleNamespace(
            database=SimpleNamespace(db_type=DataSourceTypeEnum.MYSQL.value),
        )
        with self.assertRaisesMessage(AutoApiError, '包含写入行为'):
            DataSourceExecutionRequestService.execute_operation(
                project_product_id=1,
                datasource_alias_id=2,
                test_env=3,
                operation_config='UPDATE users SET name = name',
            )
        execute.assert_not_called()

    @patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.finish_success')
    @patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionAuditService.start')
    @patch('src.apps.data_factory.services.datasource.data_source_execution.DataFactoryDatasource.create_engine')
    @patch(
        'src.apps.data_factory.services.datasource.data_source_execution.DataFactoryDatasourceResolver.require_binding_permission')
    @patch('src.apps.data_factory.services.datasource.data_source_execution.DataFactoryDatasourceResolver.resolve_binding_by_env')
    def test_query_returns_structured_limited_result(
            self,
            resolve_binding: Mock,
            require_permission: Mock,
            create_engine: Mock,
            audit_start: Mock,
            audit_finish: Mock,
    ):
        rows = [SimpleNamespace(_mapping={'id': index}) for index in range(101)]
        engine = FakeEngine(FakeResult(rows=rows, rowcount=-1))
        create_engine.return_value = engine
        resolve_binding.return_value = SimpleNamespace(
            datasource_alias_id=2,
            database_id=3,
            db_c_status=1,
            db_rud_status=1,
            database=SimpleNamespace(
                db_type=DataSourceTypeEnum.MYSQL.value,
                password='secret',
            ),
        )
        audit_start.return_value = SimpleNamespace(
            existing=False,
            record=SimpleNamespace(id=11, is_slow=False),
        )

        result = DataSourceExecutionService.execute(
            project_product_id='1',
            datasource_alias_id='2',
            test_env='3',
            operation_config='SELECT id FROM users',
        )

        resolve_binding.assert_called_once_with(2, 1, 3)
        require_permission.assert_called_once_with(resolve_binding.return_value, write=False)
        self.assertTrue(engine.connect_called)
        self.assertFalse(engine.begin_called)
        self.assertTrue(engine.disposed)
        self.assertEqual(result['execution_type'], 'query')
        self.assertEqual(result['row_count'], 100)
        self.assertTrue(result['truncated'])
        audit_start.assert_called_once()
        audit_finish.assert_called_once()

    def test_failed_business_sql_finishes_audit_as_failure(self):
        binding = SimpleNamespace(
            datasource_alias_id=2,
            database_id=3,
            db_c_status=1,
            db_rud_status=1,
            database=SimpleNamespace(
                db_type=DataSourceTypeEnum.MYSQL.value,
                password='secret',
            ),
        )
        handle = SimpleNamespace(
            existing=False,
            record=SimpleNamespace(id=12, is_slow=False),
        )
        with patch(
                'src.apps.data_factory.services.datasource.data_source_execution.'
                'DataFactoryDatasourceResolver.resolve_binding_by_env',
                return_value=binding,
        ), patch(
            'src.apps.data_factory.services.datasource.data_source_execution.'
            'DataFactoryDatasourceResolver.require_binding_permission',
        ), patch(
            'src.apps.data_factory.services.sql.sql_execution_audit.'
            'SqlExecutionAuditService.start',
            return_value=handle,
        ), patch(
            'src.apps.data_factory.services.sql.sql_execution_audit.'
            'SqlExecutionAuditService.finish_failure',
        ) as finish_failure, patch.object(
            DataSourceExecutionService,
            'execute_sql',
            side_effect=AutoApiError(
                ErrorDefinition(code=300, message='执行失败')
            ),
        ):
            with self.assertRaises(AutoApiError):
                DataSourceExecutionService.execute(
                    project_product_id=1,
                    datasource_alias_id=2,
                    test_env=3,
                    operation_config='DELETE FROM users WHERE id = 1',
                    source_context={
                        'source_type': 'api_case',
                        'source_stage': 'case_posterior',
                        'source_id': 51,
                    },
                )

        finish_failure.assert_called_once()

    def test_elasticsearch_config_requires_standard_json_object(self):
        config = DataSourceExecutionService.normalize_elasticsearch_config({
            'index': 'orders-*',
            'query': {'query': {'match_all': {}}},
        })
        self.assertEqual(config['index'], 'orders-*')
        with self.assertRaisesMessage(Exception, '必须是JSON对象'):
            DataSourceExecutionService.normalize_elasticsearch_config('not-json')
