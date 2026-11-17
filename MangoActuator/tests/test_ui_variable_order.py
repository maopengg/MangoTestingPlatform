from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from mangotools.enums import StatusEnum, UiPublicTypeEnum
from src.customization import ObtainTestData
from src.exceptions import UiError
from src.services.ui.page_steps import PageSteps
from src.services.ui.test_case import TestCase


class UiVariableOrderTest(IsolatedAsyncioTestCase):
    def make_case(self, step_count=2):
        service = TestCase.__new__(TestCase)
        service.test_data = ObtainTestData()
        service.base_data = SimpleNamespace(
            test_data=service.test_data,
            set_database_execute_callback=MagicMock(),
        )
        service.web_runtime = MagicMock()
        service.case_model = SimpleNamespace(
            id=1, name='variable order', test_env=2, project_product=3,
            execution_id='run-1', slot_id=None, executor_connection_id=None,
            test_suite_details=None, send_user=None,
            steps=[SimpleNamespace(name=f'step-{i}') for i in range(step_count)],
            front_custom=[{'key': 'front_read', 'value': '${{code_value}}'}],
            front_sql=[], posterior_sql=[],
            parametrize=[{'key': 'shared', 'value': '${{front_read}}'}],
        )
        service.case_result = SimpleNamespace(status=StatusEnum.SUCCESS.value, error_message=None)
        service._runtime_execution_id = 'run-1'
        service._runtime_execution_aliases = set()
        for method in ('refresh_runtime_config', 'case_posterior', 'sava_videos',
                       'send_case_result', 'apply_ui_auth_cache'):
            setattr(service, method, AsyncMock())
        service.set_page_steps = MagicMock()
        return service

    def make_page(self, service):
        page = PageSteps.__new__(PageSteps)
        page.base_data = service.base_data
        page.web_runtime = service.web_runtime
        page.case_id = 1
        page._data_source_callback = object()
        page.page_steps_model = SimpleNamespace(
            id=10, project_product=3, test_env=2, environment_config={},
            public_data_list=[
                SimpleNamespace(type=UiPublicTypeEnum.CUSTOM.value, key='shared', value='default'),
                SimpleNamespace(type=UiPublicTypeEnum.SQL.value, key='sql_value',
                                value='SELECT 1', datasource_alias=1),
                SimpleNamespace(type=UiPublicTypeEnum.CODE.value, key='code', value=(
                    'def variable(context):\n'
                    '    return {"code_value": context.test_data.get_cache("sql_value") + "-code"}'
                )),
            ],
        )
        page.page_step_result_model = SimpleNamespace(status=StatusEnum.SUCCESS.value)
        page.driver_init = AsyncMock()
        page.steps_main = AsyncMock(return_value=page.page_step_result_model)
        return page

    async def test_globals_precede_front_and_parameters_without_page_reload(self):
        service = self.make_case()
        service.case_model.front_sql = [
            {'datasource_alias': 1, 'sql': 'SELECT ${{code_value}}', 'key_list': ['front_sql']}
        ]
        service.case_model.parametrize = [{'key': 'shared', 'value': '${{front_sql}}'}]
        pages = [self.make_page(service), self.make_page(service)]
        events = []

        async def execute(**kwargs):
            self.assertEqual(service.test_data.get_cache('shared'), 'default')
            if kwargs['source_context']['source_stage'] == 'global_variable':
                kwargs['test_data'].set_cache('sql_value', 'sql')
                events.append('global_sql')
            else:
                self.assertEqual(kwargs['item']['sql'], 'SELECT sql-code')
                self.assertEqual(service.test_data.get_cache('front_read'), 'sql-code')
                kwargs['test_data'].set_cache('front_sql', 'sql-code-front')
                events.append('front_sql')

        async def driver():
            self.assertEqual(service.test_data.get_cache('front_read'), 'sql-code')
            self.assertEqual(service.test_data.get_cache('shared'), 'sql-code-front')
            events.append('driver')

        async def auth():
            events.append('auth')

        for page in pages:
            page.driver_init.side_effect = driver
        service.apply_ui_auth_cache.side_effect = auth
        with patch.object(service, '_create_page_steps', side_effect=pages) as create, \
                patch('src.services.ui.page_steps.UiDataSourceExecutionService.execute',
                      new=AsyncMock(side_effect=execute)) as sql, \
                patch('src.services.ui.test_case.UiRuntimeRegistry.register', new_callable=AsyncMock), \
                patch('src.services.ui.test_case.ExecutionActivity.update'), \
                patch('src.tools.decorator.memory.psutil.virtual_memory',
                      return_value=SimpleNamespace(percent=0)):
            await service.case_main()

        self.assertEqual(create.call_count, 2)
        self.assertEqual(sql.await_count, 2)
        self.assertEqual(events, ['global_sql', 'front_sql', 'driver', 'auth', 'driver', 'auth'])
        self.assertEqual(service.test_data.get_cache('shared'), 'sql-code-front')
        for page in pages:
            page.steps_main.assert_awaited_once()
        service.send_case_result.assert_awaited_once()

    async def test_global_failure_stops_front_parameters_and_actions(self):
        service = self.make_case(1)
        page = self.make_page(service)
        page.page_init = AsyncMock(side_effect=UiError(300, 'global failed'))
        service.case_front = AsyncMock()
        service.case_parametrize = AsyncMock()
        with patch.object(service, '_create_page_steps', return_value=page), \
                patch('src.tools.executor_task_context.is_executor_task', return_value=True), \
                patch('src.tools.decorator.memory.psutil.virtual_memory',
                      return_value=SimpleNamespace(percent=0)):
            with self.assertRaises(UiError):
                await service.case_main()
        service.case_front.assert_not_awaited()
        service.case_parametrize.assert_not_awaited()
        page.driver_init.assert_not_awaited()
        page.steps_main.assert_not_awaited()
        self.assertEqual(service.case_result.status, StatusEnum.FAIL.value)
        self.assertEqual(service.case_result.error_message, 'global failed')
        service.send_case_result.assert_awaited_once()

    async def test_empty_case_does_not_construct_page(self):
        service = self.make_case(0)
        service.case_model.front_custom = []
        service.case_model.parametrize = []
        with patch.object(service, '_create_page_steps') as create, \
                patch('src.tools.decorator.memory.psutil.virtual_memory',
                      return_value=SimpleNamespace(percent=0)):
            await service.case_main()
        create.assert_not_called()
        service.send_case_result.assert_awaited_once()
