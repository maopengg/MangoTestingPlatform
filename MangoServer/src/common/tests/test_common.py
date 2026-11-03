import json
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from mangotools.exceptions import MangoToolsError
from rest_framework.exceptions import ValidationError

from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.storage import MangoMinioMediaStorage
from src.common.testing import ObtainAssertion, ObtainTestData

PytestCase = apps.get_model("auto_pytest", "PytestCase")
UserLogsMiddleWare = import_module(
    "src.apps.user.middleware.user_logs"
).UserLogsMiddleWare
mango_exception_handler = import_module(
    "src.apps.system.middleware.exception_handler"
).mango_exception_handler


class UserLogsSensitiveDataTests(SimpleTestCase):

    def test_public_mock_runtime_skips_general_operation_log(self):
        request = RequestFactory().get('/api/mock/sample')
        response = HttpResponse('ok')
        middleware = UserLogsMiddleWare(lambda _: response)

        with patch('src.apps.user.middleware.user_logs.UserLogService.submit') as submit:
            self.assertIs(middleware.process_response(request, response), response)

        submit.assert_not_called()

    def test_mock_config_management_still_uses_general_operation_log(self):
        request = RequestFactory().get('/api/api/mock/config/detail?id=1')
        response = HttpResponse('ok')
        middleware = UserLogsMiddleWare(lambda _: response)

        with patch('src.apps.user.middleware.user_logs.UserLogService.submit') as submit:
            middleware.process_response(request, response)

        submit.assert_called_once()

    def test_redacts_nested_sensitive_fields(self):
        data = {
            'username': 'mango',
            'new_password': 'new-secret',
            'payload': {
                'confirm_password': 'new-secret',
                'items': [
                    {'token': 'token-value'},
                    {'api-key': 'api-key-value'},
                    {'Authorization': 'Bearer token'},
                ],
            },
        }

        redacted = UserLogsMiddleWare._redact_sensitive(data)

        self.assertEqual(redacted['username'], 'mango')
        self.assertEqual(redacted['new_password'], '***')
        self.assertEqual(redacted['payload']['confirm_password'], '***')
        self.assertEqual(redacted['payload']['items'][0]['token'], '***')
        self.assertEqual(redacted['payload']['items'][1]['api-key'], '***')
        self.assertEqual(redacted['payload']['items'][2]['Authorization'], '***')

    def test_does_not_redact_non_secret_token_configuration(self):
        data = {'token_ttl': 1440, 'authorization_mode': 'bearer'}

        self.assertEqual(UserLogsMiddleWare._redact_sensitive(data), data)


class ModelCRUDPaginationTests(SimpleTestCase):

    @staticmethod
    def pytest_crud():
        crud = ModelCRUD()
        crud.model = PytestCase
        return crud

    def test_in_filter_values_support_comma_separated_ids(self):
        self.assertEqual(ModelCRUD.parse_in_filter_values(['1,2', '3']), ['1', '2', '3'])

    def test_complete_paging_params_are_removed_from_model_filters(self):
        query_dict = {'page': '1', 'pageSize': '20', 'status': '1'}

        paging = ModelCRUD.pop_paging_params(query_dict)

        self.assertTrue(paging)
        self.assertEqual(query_dict, {'status': '1'})

    def test_incomplete_paging_params_are_removed_from_model_filters(self):
        query_dict = {'page': '1', 'status': '1'}

        paging = ModelCRUD.pop_paging_params(query_dict)

        self.assertFalse(paging)
        self.assertEqual(query_dict, {'status': '1'})

    def test_explicit_file_path_lookups_are_preserved(self):
        crud = self.pytest_crud()

        self.assertTrue(crud.has_explicit_lookup_or_transform('file_path__exact'))
        self.assertTrue(crud.has_explicit_lookup_or_transform('file_path__startswith'))

    def test_plain_and_related_text_fields_still_use_contains_search(self):
        crud = self.pytest_crud()

        self.assertFalse(crud.has_explicit_lookup_or_transform('name'))
        self.assertFalse(crud.has_explicit_lookup_or_transform('project_product__name'))
        self.assertTrue(crud.supports_contains_search('name'))
        self.assertTrue(crud.supports_contains_search('project_product__name'))

    def test_foreign_key_field_uses_exact_search(self):
        crud = self.pytest_crud()

        self.assertFalse(crud.supports_contains_search('project_product'))


class ErrorResponseTests(SimpleTestCase):
    @patch('src.common.responses.model_crud.report_validation_failure')
    def test_crud_invalid_create_and_update_report_without_request_values(self, report):
        errors = {'target_address': ['This field may not be null.']}
        serializer = MagicMock()
        serializer.is_valid.return_value = False
        serializer.errors = errors
        crud = ModelCRUD()
        crud.model = MagicMock()
        crud.serializer = MagicMock(return_value=serializer)
        crud.with_update_user = lambda request, data: data
        crud.has_data_scope_permission = lambda *args: True
        crud.has_instance_data_scope_permission = lambda *args: True
        crud.validate_business_module = lambda *args: None
        request = SimpleNamespace(data={'id': 1, 'custom_code': 'secret-code'},
                                  method='POST', path='/api/example/config', user={})
        for method in (crud.post, crud.put):
            with self.subTest(method=method.__name__):
                response = method(request)
                self.assertEqual(response.data['code'], 300)
                self.assertEqual(response.data['data'], errors)
        self.assertEqual(report.call_count, 2)
        self.assertEqual(report.call_args.args, (errors,))
        self.assertIs(report.call_args.kwargs['request'], request)
        serializer.save.assert_not_called()

    @patch('src.common.decorators.system_error.import_string', side_effect=RuntimeError('unavailable'))
    def test_diagnostic_adapter_failure_does_not_replace_validation_response(self, reporter):
        class TestView:
            @error_response('system')
            def post(self, request):
                raise ValidationError({'name': ['bad']})

        response = TestView().post(SimpleNamespace(user={}))
        self.assertEqual(response.data['code'], 300)
        reporter.assert_called_once()

    @patch('src.common.decorators.error_response.report_validation_failure')
    @patch('src.common.decorators.error_response.report_system_error')
    def test_validation_error_returns_business_response_with_diagnostic(self, report_system_error, report_validation):
        class TestView:
            @error_response('system')
            def post(self, _request):
                raise ValidationError({'project_product': ['This field is required.']})

        response = TestView().post(SimpleNamespace(user={}))

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '参数校验错误')
        self.assertIn('project_product', response.data['data'])
        report_system_error.assert_not_called()
        report_validation.assert_called_once()

    @patch('src.common.decorators.error_response.report_system_error')
    def test_missing_object_returns_business_response_without_system_record(self, report_system_error):
        class TestView:
            @error_response('system')
            def get(self, _request):
                raise ObjectDoesNotExist('internal model name must not be exposed')

        response = TestView().get(SimpleNamespace(user={}))

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '指定的数据不存在或已删除，请重新查询后使用有效ID')
        self.assertIsNone(response.data['data'])
        report_system_error.assert_not_called()

    @patch('src.common.decorators.error_response.report_system_error')
    def test_unknown_error_still_creates_system_record(self, report_system_error):
        class TestView:
            @error_response('system')
            def get(self, _request):
                raise RuntimeError('boom')

        request = SimpleNamespace(user={})
        response = TestView().get(request)

        self.assertEqual(response.data['code'], 1000)
        report_system_error.assert_called_once()
        self.assertIsInstance(report_system_error.call_args.args[0], RuntimeError)


class GlobalExceptionHandlerTests(SimpleTestCase):
    @patch('src.apps.system.middleware.exception_handler.report_validation_failure')
    def test_normal_auth_permission_and_throttle_rejections_are_not_collected(self, report):
        from rest_framework.exceptions import NotAuthenticated, PermissionDenied, Throttled
        for error in (NotAuthenticated(), PermissionDenied(), Throttled()):
            mango_exception_handler(error, {'request': None})
        report.assert_not_called()

    @patch('src.apps.system.middleware.exception_handler.report_validation_failure')
    def test_validation_error_records_diagnostic_without_changing_response(self, report):
        request = SimpleNamespace(method='POST', path='/api/example/config')
        response = mango_exception_handler(ValidationError({'name': ['bad']}), {'request': request})
        self.assertEqual(response.data['code'], 300)
        report.assert_called_once()
        self.assertIs(report.call_args.kwargs['request'], request)

    @patch('src.apps.system.middleware.exception_handler.report_system_error')
    def test_missing_object_returns_protocol_neutral_business_response(self, report_system_error):
        response = mango_exception_handler(
            ObjectDoesNotExist('internal model name'),
            {'request': None},
        )

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '指定的数据不存在或已删除，请重新查询后使用有效ID')
        report_system_error.assert_not_called()


class MangoMinioMediaStorageTests(SimpleTestCase):

    @staticmethod
    def storage():
        storage = object.__new__(MangoMinioMediaStorage)
        storage.location = 'mango-testing-platform/master'
        storage.legacy_locations = [
            'auto_test_report/master',
            'auto_test_report/test',
            'auto_test_report/dev',
            'mango-testing-platform/test',
            'mango-testing-platform/dev',
        ]
        return storage

    def test_new_upload_uses_master_location(self):
        self.assertEqual(
            self.storage()._prefix_name('test_file/example.docx'),
            'mango-testing-platform/master/test_file/example.docx',
        )

    def test_legacy_upload_name_is_normalized_to_master_location(self):
        self.assertEqual(
            self.storage()._prefix_name('auto_test_report/test/test_file/example.docx'),
            'mango-testing-platform/master/test_file/example.docx',
        )

    def test_legacy_paths_remain_read_candidates(self):
        candidates = self.storage()._name_candidates(
            'auto_test_report/test/test_file/example.docx',
        )
        self.assertEqual(candidates[0], 'mango-testing-platform/master/test_file/example.docx')
        self.assertIn('auto_test_report/test/test_file/example.docx', candidates)


class ObtainTestDataReplacementTests(SimpleTestCase):

    def test_replace_reads_data_factory_cache_with_template_alias(self):
        test_data = ObtainTestData()
        test_data.set_data_factory_cache("智能审查任务.task_id", 1234577813)

        self.assertEqual(test_data.replace("${{智能审查任务.task_id}}"), 1234577813)
        self.assertEqual(test_data.replace("${{df.智能审查任务.task_id}}"), 1234577813)

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

    def test_replace_can_preserve_only_missing_cache_placeholders_for_api_info_debug(self):
        test_data = ObtainTestData()
        test_data.set_cache("known_value", "V100")

        with test_data.preserve_unresolved_cache_placeholders():
            result = test_data.replace(
                "https://example.com/vendors/${{known_value}}/${{vendor_id}}"
            )

        self.assertEqual(
            result,
            "https://example.com/vendors/V100/${{vendor_id}}",
        )
        with self.assertRaises(MangoToolsError):
            test_data.replace("${{vendor_id}}")

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

    def test_set_sql_cache_maps_multiple_keys_by_column_name(self):
        test_data = ObtainTestData()

        test_data.set_sql_cache("id,name", {"name": "mango", "id": 21})

        self.assertEqual(test_data.get_cache("id"), 21)
        self.assertEqual(test_data.get_cache("name"), "mango")

    def test_set_sql_cache_falls_back_to_column_order_when_key_not_in_row(self):
        test_data = ObtainTestData()

        test_data.set_sql_cache("id,name", {"id": 21, "neme": "mango"})

        self.assertEqual(test_data.get_cache("id"), 21)
        self.assertEqual(test_data.get_cache("name"), "mango")

    def test_set_sql_cache_keeps_single_key_first_column_behavior(self):
        test_data = ObtainTestData()

        test_data.set_sql_cache("user", {"id": 21, "name": "mango"})

        self.assertEqual(test_data.get_cache("user"), 21)


class ObtainAssertionTests(SimpleTestCase):

    def test_equal_assertion_accepts_same_numeric_values_with_different_runtime_types(self):
        result = ObtainAssertion().ass("p_is_equal_to", actual=110000, expect=110000)

        self.assertEqual(result, "实际=110000, 预期=110000")

    def test_equal_assertion_accepts_same_boolean_values_with_different_runtime_types(self):
        result = ObtainAssertion().ass("p_is_equal_to", actual=False, expect=False)

        self.assertEqual(result, "实际=False, 预期=False")

    def test_assertion_group_supports_and_or_and_typed_values(self):
        from src.apps.system.api.views.system_api import SystemViews

        result = SystemViews._execute_assertion_test_groups([
            {
                'name': '数值且关系',
                'logic': 'AND',
                'items': [
                    {'method': 'p_number_equal', 'actual': 1, 'expect': '1.0'},
                    {'method': 'p_is_integer', 'actual': 1},
                ],
            },
            {
                'name': '或关系',
                'logic': 'OR',
                'items': [
                    {'method': 'p_is_positive', 'actual': -1},
                    {'method': 'p_is_negative', 'actual': -1},
                ],
            },
        ])

        self.assertTrue(result['status'])
        self.assertEqual(len(result['groups']), 2)
        self.assertFalse(result['groups'][1]['items'][0]['status'])
        self.assertTrue(result['groups'][1]['items'][1]['status'])
