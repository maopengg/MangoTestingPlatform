from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from src.services.data_source_execution import (
    UiDataSourceExecutionCallback,
    UiDataSourceExecutionService,
)
from src.services.ui.page_steps import PageSteps
from src.services.ui.test_case import TestCase


class UiDataSourceExecutionServiceTest(IsolatedAsyncioTestCase):
    def test_business_runtime_has_no_direct_database_connection_entry(self):
        source_root = Path(__file__).resolve().parents[1] / 'src'
        forbidden = (
            'set_mysql(',
            'create_database_connection(',
            'pymysql',
            'mysql.connector',
            'sqlalchemy.create_engine',
        )
        violations = []
        for path in source_root.rglob('*.py'):
            if 'storage/sqlite' in path.as_posix():
                continue
            content = path.read_text(encoding='utf-8')
            for marker in forbidden:
                if marker in content:
                    violations.append(f'{path.relative_to(source_root)}: {marker}')

        self.assertEqual(violations, [])

    async def test_page_init_only_binds_platform_callback(self):
        service = PageSteps.__new__(PageSteps)
        callback = object()
        service._data_source_callback = callback
        service.page_steps_model = SimpleNamespace(public_data_list=[])
        service.base_data = SimpleNamespace(
            set_database_execute_callback=MagicMock(),
            set_mysql=MagicMock(),
        )

        await service.page_init(False)

        service.base_data.set_database_execute_callback.assert_called_once_with(callback)
        service.base_data.set_mysql.assert_not_called()

    @patch(
        'src.services.ui.test_case.UiDataSourceExecutionService.execute',
        new_callable=AsyncMock,
    )
    async def test_ui_case_database_operations_only_run_in_selected_environment(self, execute):
        service = TestCase.__new__(TestCase)
        service.case_model = SimpleNamespace(project_product=22, test_env=2, id=51)
        service.base_data = SimpleNamespace(
            test_data=SimpleNamespace(
                replace=lambda value: value,
                set_cache=MagicMock(),
            )
        )

        await service.case_front([], [
            {'datasource_alias': 1, 'sql': 'SELECT 1', 'test_envs': [1]},
            {'datasource_alias': 2, 'sql': 'SELECT 2', 'test_envs': [2]},
            {'datasource_alias': 3, 'sql': 'SELECT 3', 'test_envs': []},
        ])

        self.assertEqual(execute.await_count, 2)
        self.assertEqual(
            [call.kwargs['item']['datasource_alias'] for call in execute.await_args_list],
            [2, 3],
        )

        execute.reset_mock()
        await service.case_posterior([
            {'datasource_alias': 4, 'sql': 'DELETE FROM t1', 'test_envs': [1]},
            {'datasource_alias': 5, 'sql': 'DELETE FROM t2', 'test_envs': [2]},
        ])

        execute.assert_awaited_once()
        self.assertEqual(execute.await_args.kwargs['item']['datasource_alias'], 5)

    @patch(
        'src.services.ui.page_steps.UiDataSourceExecutionService.execute',
        new_callable=AsyncMock,
    )
    async def test_ui_custom_code_callable_uses_unified_service(self, execute):
        execute.return_value = {'rows': [{'id': 1}]}
        service = PageSteps.__new__(PageSteps)
        service.page_steps_model = SimpleNamespace(project_product=22, test_env=1, id=18)
        service.base_data = SimpleNamespace(test_data=MagicMock())
        service.case_id = 51

        result = await service._execute_custom_data_source(9, 'SELECT id FROM users')

        self.assertEqual(result, {'rows': [{'id': 1}]})
        execute.assert_awaited_once_with(
            item={'datasource_alias': 9, 'value': 'SELECT id FROM users'},
            project_product_id=22,
            test_env=1,
            test_data=service.base_data.test_data,
            require_cache_result=False,
            confirm_write=True,
            source_context={
                'source_type': 'ui_custom_code',
                'source_stage': 'custom_code',
                'source_id': 51,
                'case_id': 51,
                'page_step_id': 18,
            },
        )

    @patch(
        'src.services.data_source_execution.UiDataSourceExecutionService.execute',
        new_callable=AsyncMock,
    )
    async def test_third_party_callback_returns_platform_rows(self, execute):
        execute.return_value = {'rows': [{'id': 1}, {'id': 2}]}
        callback = UiDataSourceExecutionCallback(
            project_product_id=22,
            test_env=1,
            test_data=MagicMock(),
            source_context={
                'source_type': 'ui_case',
                'source_stage': 'page_step',
                'source_id': 51,
            },
        )

        result = await callback(
            operation_config='select id from user',
            datasource_alias_id=9,
            source_context={'source_stage': 'sql_assertion', 'element_id': 18},
        )

        self.assertEqual(result, [{'id': 1}, {'id': 2}])
        self.assertEqual(
            execute.await_args.kwargs['source_context'],
            {
                'source_type': 'ui_case',
                'source_stage': 'sql_assertion',
                'source_id': 51,
                'element_id': 18,
            },
        )

    async def test_sql_rows_are_cached_with_legacy_key_list(self):
        test_data = SimpleNamespace(
            replace=lambda value: value,
            set_sql_cache=MagicMock(),
        )

        with patch(
            'src.services.data_source_execution.HTTP.data_source.execute',
            new_callable=AsyncMock,
            return_value={'rows': [{'id': 7, 'name': '用户'}]},
        ) as execute:
            await UiDataSourceExecutionService.execute(
                item={
                    'datasource_alias': 12,
                    'sql': 'select id, name from user limit 1',
                    'key_list': ['id', 'name'],
                },
                project_product_id=22,
                test_env=1,
                test_data=test_data,
                require_cache_result=True,
            )

        execute.assert_awaited_once_with(
            datasource_alias_id=12,
            project_product_id=22,
            test_env=1,
            operation_config='select id, name from user limit 1',
            confirm_write=True,
            source_context={
                'source_type': 'ui_runtime',
                'source_stage': 'database_operation',
            },
            request_id=ANY,
        )
        test_data.set_sql_cache.assert_called_once_with('id,name', {'id': 7, 'name': '用户'})

    async def test_elasticsearch_source_is_cached_without_changing_item_shape(self):
        test_data = SimpleNamespace(
            replace=lambda value: value,
            set_sql_cache=MagicMock(),
        )

        operation = {'index': 'orders', 'query': {'match_all': {}}}
        with patch(
            'src.services.data_source_execution.HTTP.data_source.execute',
            new_callable=AsyncMock,
            return_value={'rows': [{'_source': {'order_no': 'M001'}}]},
        ):
            await UiDataSourceExecutionService.execute(
                item={'datasource_alias': 13, 'sql': operation, 'key_list': 'order_no'},
                project_product_id=22,
                test_env=1,
                test_data=test_data,
            )

        test_data.set_sql_cache.assert_called_once_with('order_no', {'order_no': 'M001'})

    async def test_redis_hgetall_result_is_normalized_for_cache(self):
        test_data = SimpleNamespace(
            replace=lambda value: value,
            set_sql_cache=MagicMock(),
        )

        with patch(
            'src.services.data_source_execution.HTTP.data_source.execute',
            new_callable=AsyncMock,
            return_value={
                'command': 'HGETALL',
                'result': ['name', 'mango', 'role', 'admin'],
            },
        ):
            await UiDataSourceExecutionService.execute(
                item={
                    'datasource_alias': 14,
                    'sql': 'HGETALL user:1',
                    'key_list': 'name,role',
                },
                project_product_id=22,
                test_env=1,
                test_data=test_data,
            )

        test_data.set_sql_cache.assert_called_once_with(
            'name,role',
            {'name': 'mango', 'role': 'admin'},
        )


if __name__ == '__main__':
    import unittest

    unittest.main()
