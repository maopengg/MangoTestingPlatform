from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.api.serializers.api_case_detailed_parameter_mutation import (
    ApiCaseDetailedParameterSerializers,
)
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.schemas.execution import ApiExecutionResponse
from src.apps.auto_api.services.api_case.parameter_validation import ApiCaseParameterValidationService
from src.apps.auto_api.services.base.case_parameter import CaseParameter


class FakeTestData:

    def replace(self, value):
        return value


class FakeConnection:

    def __init__(self, result):
        self.result = result
        self.executed_sql = []

    def condition_execute(self, sql):
        self.executed_sql.append(sql)
        return self.result


class SqlAssertionChainTests(SimpleTestCase):

    @staticmethod
    def parameter(sql_config):
        return SimpleNamespace(
            id=1,
            body_config={},
            ass_jsonpath=[],
            ass_sql=sql_config if isinstance(sql_config, list) else [sql_config],
            ass_general=[],
            ass_json_all=None,
            ass_text_all=None,
            ass_schema=None,
        )

    @staticmethod
    def response():
        return ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={},
            text='',
        )

    def case_parameter(self, sql_config, sql_result):
        connection = FakeConnection(sql_result)
        test_setup = SimpleNamespace(
            test_data=FakeTestData(),
            test_object=SimpleNamespace(id=1, project_product_id=22),
        )
        api_info = SimpleNamespace(is_schema=0, ass_schema=None)
        return (
            CaseParameter(
                test_setup,
                self.parameter(sql_config),
                api_info,
                test_env=0,
            ),
            connection,
        )

    def test_regular_execution_runs_sql_and_records_source(self):
        sql_config = {
            'actual': 'SELECT id FROM demo',
            'method': 'assert_sql_count',
            'expect': '2',
            'datasource_alias': 7,
        }
        case_parameter, connection = self.case_parameter(
            sql_config,
            [{'id': 1}, {'id': 2}],
        )

        with patch(
                'src.apps.auto_api.services.base.data_source_operation.DataSourceExecutionService.execute',
                return_value={'rows': connection.result},
        ) as execute:
            results, status, error_message = case_parameter.ass_main(self.response())

        self.assertEqual(status, StatusEnum.SUCCESS.value)
        self.assertIsNone(error_message)
        execute.assert_called_once_with(
            datasource_alias_id=7,
            project_product_id=22,
            test_env=0,
            operation_config='SELECT id FROM demo',
            source_context={
                'source_type': 'api_case_parameter',
                'source_stage': 'sql_assertion',
                'source_id': 1,
                'case_id': None,
                'parameter_id': 1,
                'api_info_id': None,
                'operation_index': 1,
            },
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, 'sql')
        self.assertEqual(results[0].actual_source, 'SELECT id FROM demo')
        self.assertEqual(results[0].raw_config, sql_config)

    def test_regular_execution_skips_sql_assertion_outside_current_environment(self):
        sql_config = {
            'actual': 'SELECT id FROM demo',
            'method': 'assert_sql_count',
            'expect': '2',
            'datasource_alias': 7,
            'test_envs': [3],
        }
        case_parameter, _connection = self.case_parameter(sql_config, [{'id': 1}, {'id': 2}])

        with patch(
                'src.apps.auto_api.services.base.data_source_operation.DataSourceExecutionService.execute',
        ) as execute:
            results, status, error_message = case_parameter.ass_main(self.response())

        self.assertEqual(status, StatusEnum.SUCCESS.value)
        self.assertIsNone(error_message)
        self.assertEqual(results, [])
        execute.assert_not_called()

    def test_regular_execution_returns_failed_sql_assertion_result(self):
        sql_config = {
            'actual': 'SELECT id FROM demo',
            'method': 'assert_sql_count',
            'expect': '2',
            'datasource_alias': 8,
        }
        case_parameter, connection = self.case_parameter(
            sql_config,
            [{'id': 1}],
        )

        with patch(
                'src.apps.auto_api.services.base.data_source_operation.DataSourceExecutionService.execute',
                return_value={'rows': connection.result},
        ):
            results, status, error_message = case_parameter.ass_main(self.response())

        self.assertEqual(status, StatusEnum.FAIL.value)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, 'sql')
        self.assertEqual(results[0].status, StatusEnum.FAIL.value)
        self.assertIn('SQL断言失败', error_message)
        self.assertIn('实际条数=1', results[0].ass_msg)

    def test_assertion_verification_also_runs_sql(self):
        sql_config = {
            'actual': 'SELECT name FROM demo',
            'method': 'assert_sql_starts_with',
            'expect': '示例',
            'datasource_alias': 3,
        }
        case_parameter, connection = self.case_parameter(
            sql_config,
            [{'name': '示例项目'}],
        )

        with patch(
                'src.apps.auto_api.services.base.data_source_operation.DataSourceExecutionService.execute',
                return_value={'rows': connection.result},
        ):
            results, status, error_message = case_parameter.verify_all_assertions(
                self.response(),
            )

        self.assertEqual(status, StatusEnum.SUCCESS.value)
        self.assertIsNone(error_message)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_type, 'sql')

    def test_regular_execution_collects_all_sql_assertion_failures(self):
        sql_configs = [
            {
                'actual': 'SELECT id FROM demo',
                'method': 'assert_sql_count',
                'expect': '2',
                'datasource_alias': 3,
            },
            {
                'actual': 'SELECT id FROM demo',
                'method': 'assert_sql_count',
                'expect': '3',
                'datasource_alias': 3,
            },
        ]
        case_parameter, connection = self.case_parameter(sql_configs, [{'id': 1}])

        with patch(
                'src.apps.auto_api.services.base.data_source_operation.DataSourceExecutionService.execute',
                return_value={'rows': connection.result},
        ) as execute:
            results, status, error_message = case_parameter.ass_main(self.response())

        self.assertEqual(status, StatusEnum.FAIL.value)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.status == StatusEnum.FAIL.value for item in results))
        self.assertIn('SQL断言失败（第1项）', error_message)
        self.assertIn('SQL断言失败（第2项）', error_message)
        self.assertIn('实际条数=1', results[0].ass_msg)
        self.assertIn('实际条数=1', results[1].ass_msg)

    def test_regular_execution_collects_all_response_assertion_failures(self):
        parameter = SimpleNamespace(
            body_config={},
            ass_jsonpath=[
                {
                    'assertion_type': 'jsonpath',
                    'actual': '$.code',
                    'method': 'p_is_equal_to',
                    'expect': 0,
                },
                {
                    'assertion_type': 'jsonpath',
                    'actual': '$.status',
                    'method': 'p_is_equal_to',
                    'expect': 'ok',
                },
            ],
            ass_sql=[],
            ass_general=[],
            ass_json_all=None,
            ass_text_all=None,
            ass_schema=None,
        )
        test_setup = SimpleNamespace(
            test_data=FakeTestData(),
            test_object=SimpleNamespace(project_product_id=22),
        )
        api_info = SimpleNamespace(is_schema=0, ass_schema=None)
        case_parameter = CaseParameter(test_setup, parameter, api_info, test_env=0)
        response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'code': 500, 'status': 'failed'},
            text='failed',
        )

        results, status, error_message = case_parameter.ass_main(response)

        self.assertEqual(status, StatusEnum.FAIL.value)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(item.status == StatusEnum.FAIL.value for item in results))
        self.assertIn('实际=500，预期=0', error_message)
        self.assertIn('实际=failed，预期=ok', error_message)

    @patch(
        'src.apps.auto_api.api.serializers.api_case_detailed_parameter_mutation.validate_data_source_operation_list',
        side_effect=lambda items, *_args: items,
    )
    @patch.object(ApiCaseDetailedParameterSerializers, '_project_product_id', return_value=22)
    def test_save_validation_rejects_invalid_sql_assertion_config(
            self,
            _project_product_id,
            _validate_datasource,
    ):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaisesMessage(AutoApiError, '断言方法【missing_method】不存在'):
            serializer.validate_ass_sql([{
                'actual': 'SELECT id FROM demo',
                'method': 'missing_method',
                'expect': '1',
                'datasource_alias': 7,
            }])

        with self.assertRaisesMessage(AutoApiError, 'SQL语句不能为空'):
            serializer.validate_ass_sql([{
                'actual': '',
                'method': 'assert_sql_count',
                'expect': '1',
                'datasource_alias': 7,
            }])

        with self.assertRaisesMessage(AutoApiError, '预期值不能为空'):
            serializer.validate_ass_sql([{
                'actual': 'SELECT id FROM demo',
                'method': 'assert_sql_count',
                'expect': '',
                'datasource_alias': 7,
            }])

    @patch(
        'src.apps.auto_api.api.serializers.api_case_detailed_parameter_mutation.validate_data_source_operation_list',
        side_effect=lambda items, *_args: items,
    )
    @patch.object(ApiCaseDetailedParameterSerializers, '_project_product_id', return_value=22)
    def test_save_validation_allows_methods_without_expected_value(
            self,
            _project_product_id,
            _validate_datasource,
    ):
        serializer = ApiCaseDetailedParameterSerializers()

        result = serializer.validate_ass_sql([{
            'actual': 'SELECT name FROM demo',
            'method': 'assert_sql_is_not_empty',
            'expect': '',
            'datasource_alias': 7,
        }])

        self.assertEqual(result[0]['method'], 'assert_sql_is_not_empty')

    @patch(
        'src.apps.auto_api.services.api_case.parameter_validation.validate_data_source_operation_list',
        side_effect=lambda items, *_args: items,
    )
    def test_service_validation_accepts_and_normalizes_sql_assertion_environments(
            self,
            _validate_datasource,
    ):
        result = ApiCaseParameterValidationService.validate_sql([{
            'actual': 'SELECT name FROM demo',
            'method': 'assert_sql_is_not_empty',
            'expect': '',
            'datasource_alias': 7,
            'test_envs': [0, 3, 0],
        }], project_product_id=22)

        self.assertEqual(result[0]['test_envs'], [0, 3])
        _validate_datasource.assert_called_once_with([{
            'value': 'SELECT name FROM demo',
            'datasource_alias': 7,
            'test_envs': [0, 3],
        }], 'SQL断言', 22)
