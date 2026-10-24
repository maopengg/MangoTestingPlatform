# UI 领域规则测试：参数化、步骤配置、授权配置、元素自愈和结果落库。
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.auto_ui.api.serializers.ui_auth_config import UiAuthConfigSerializers
from src.apps.auto_ui.api.serializers.ui_element_mutation import PageElementSerializers
from src.apps.auto_ui.api.serializers.ui_element_presentation import PageElementSerializersC
from src.apps.auto_ui.api.serializers.ui_page_steps import PageStepsSerializers, UiOpenStepBrowserSerializer, \
    UiPageStepReferencedCasesSerializer, UiPageStepRecordingCommitSerializer, UiStepDebugControlSerializer
from src.apps.auto_ui.api.views.ui_page_steps import PageStepsViews
from src.apps.auto_ui.enums import ElementOperationEnum
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.schemas.case_schema import (
    UiCaseFrontCustomSchema,
    UiCaseFrontSqlSchema,
    UiCaseParametrizeSuite,
    UiCasePosteriorSqlSchema,
    validate_data_source_items,
)
from src.apps.auto_ui.schemas.element import UiElementLocator
from src.apps.auto_ui.services.element_ai.data_sanitizer import ElementAiDataSanitizer
from src.apps.auto_ui.services.element_ai.element_ai_service import ElementAiService
from src.apps.auto_ui.services.page_step_asset_service import PageStepAssetService
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService
from src.apps.auto_ui.services.page_step_flow_service import PageStepFlowService
from src.apps.auto_ui.services.page_step_recording import PageStepRecordingService
from src.apps.auto_ui.services.test_case import test_case as ui_test_case_module
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.apps.auto_ui.services.test_report_writing import TestReportWriting


class UiPageStepReferencedCasesTests(SimpleTestCase):

    def test_reference_query_accepts_positive_page_step_id(self):
        serializer = UiPageStepReferencedCasesSerializer(data={'page_step_id': '8'})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['page_step_id'], 8)

    def test_reference_query_rejects_missing_page_step_id(self):
        request = Request(APIRequestFactory().get('/api/ui/page/steps/cases'))

        response = PageStepsViews().referenced_cases(request)

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '查询页面步骤引用用例参数不正确')
        self.assertIn('page_step_id', response.data['data'])

    @patch(
        'src.apps.auto_ui.api.views.ui_page_steps.PageStepReferenceService.list_cases',
        return_value=[{'id': 3, 'name': '检查智能起草是否可用'}],
    )
    def test_reference_query_returns_accessible_cases(self, list_cases):
        request = Request(
            APIRequestFactory().get('/api/ui/page/steps/cases', {'page_step_id': 8})
        )

        response = PageStepsViews().referenced_cases(request)

        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['totalSize'], 1)
        self.assertEqual(response.data['data'][0]['id'], 3)
        list_cases.assert_called_once_with(request, 8)


class UiPageStepRecordingTests(SimpleTestCase):

    def test_recording_commit_serializer_accepts_ordered_nodes(self):
        serializer = UiPageStepRecordingCommitSerializer(data={
            'page_id': 12,
            'name': '录制创建订单',
            'nodes': [
                {
                    'action': 'click',
                    'detail': {'type': 0, 'ope_key': 'w_click', 'ope_value': []},
                    'element': {'locators': [{'exp': 2, 'loc': 'get_by_text("提交")'}]},
                },
                {
                    'action': 'wait',
                    'detail': {
                        'type': 0,
                        'ope_key': 'w_wait_for_timeout',
                        'ope_value': [{'f': '_time', 'v': 2}],
                    },
                },
            ],
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(len(serializer.validated_data['nodes']), 2)

    def test_recording_action_mapping_covers_three_phases(self):
        self.assertEqual(PageStepRecordingService.ACTION_METHODS['click'][0], 'w_click')
        self.assertEqual(PageStepRecordingService.ACTION_METHODS['wait'][0], 'w_wait_for_timeout')
        self.assertEqual(PageStepRecordingService.ACTION_METHODS['navigation'][0], 'w_goto')
        self.assertEqual(PageStepRecordingService.ACTION_METHODS['select'][0], 'w_select_option')
        self.assertIn('custom_variable', PageStepRecordingService.ACTION_METHODS)

    def test_recording_drag_maps_to_dominant_pixel_direction(self):
        action = {'action': 'drag', 'drag_delta_x': -120, 'drag_delta_y': 30}

        method, values = PageStepRecordingService._resolve_method(action)

        self.assertEqual(method, 'w_drag_left_pixel')
        self.assertEqual(values, [{'f': 'n', 'v': 120}])

    def test_recording_custom_variable_builds_custom_node_payload(self):
        payload = PageStepRecordingService._detail_payload(
            SimpleNamespace(
                project_product=SimpleNamespace(ui_client_type=0),
                project_product_id=1,
            ),
            {
                'action': 'custom_variable',
                'detail': {
                    'type': 3,
                    'custom': [{'key': '订单id', 'value': '123'}],
                },
            },
            2,
            4,
        )

        self.assertEqual(payload['type'], 3)
        self.assertEqual(payload['custom'], [{'key': '订单id', 'value': '123'}])
        self.assertIsNone(payload['ope_key'])

    @patch.object(PageStepDetailMutationService, 'validate_detail_payload')
    @patch.object(PageStepDetailMutationService, 'validation_method_tree')
    def test_force_wait_remains_available_as_element_operation_method(
            self,
            method_tree,
            validate_detail_payload,
    ):
        method_tree.return_value = [{
            'value': 'w_wait_for_timeout',
            'parameter': [{'f': '_time', 'd': True, 'v': 1}],
        }]
        page = SimpleNamespace(
            project_product=SimpleNamespace(ui_client_type=0),
            project_product_id=1,
        )

        payload = PageStepRecordingService._detail_payload(
            page,
            {
                'action': 'wait',
                'detail': {
                    'type': 0,
                    'ope_key': 'w_wait_for_timeout',
                    'ope_value': [{'f': '_time', 'v': 3}],
                },
            },
            2,
            4,
        )

        self.assertEqual(payload['type'], 0)
        self.assertEqual(payload['ope_key'], 'w_wait_for_timeout')
        self.assertEqual(payload['ope_value'][0]['v'], 3)
        self.assertIsNone(payload['ele_name_id'])
        validate_detail_payload.assert_called_once()

    def test_force_wait_node_payload_is_valid_without_element_or_method(self):
        payload = {
            'type': ElementOperationEnum.FORCE_WAIT.value,
            'ele_name': None,
            'ope_key': None,
            'ope_value': [{'f': 'seconds', 'v': 2.5}],
        }

        PageStepDetailMutationService.validate_detail_payload(payload)

    def test_force_wait_node_rejects_out_of_range_seconds(self):
        with self.assertRaises(AutoUiError):
            PageStepDetailMutationService.validate_detail_payload({
                'type': ElementOperationEnum.FORCE_WAIT.value,
                'ope_value': [{'f': 'seconds', 'v': 3601}],
            })

    def test_recording_force_wait_builds_independent_node_payload(self):
        page = SimpleNamespace(
            project_product=SimpleNamespace(ui_client_type=0),
            project_product_id=1,
        )

        payload = PageStepRecordingService._detail_payload(
            page,
            {
                'action': 'manual',
                'detail': {
                    'type': ElementOperationEnum.FORCE_WAIT.value,
                    'ope_value': [{'f': 'seconds', 'v': 3}],
                },
            },
            2,
            4,
        )

        self.assertEqual(payload['type'], ElementOperationEnum.FORCE_WAIT.value)
        self.assertEqual(payload['ope_value'], [{'f': 'seconds', 'v': 3}])
        self.assertIsNone(payload['ele_name_id'])
        self.assertIsNone(payload['ope_key'])

    def test_recording_rejects_condition_node(self):
        page = SimpleNamespace(
            project_product=SimpleNamespace(ui_client_type=0),
            project_product_id=1,
        )

        with self.assertRaises(AutoUiError):
            PageStepRecordingService._detail_payload(
                page,
                {'detail': {'type': 4, 'ope_key': 'w_page_to_contain_text'}},
                1,
                4,
            )

    @patch.object(PageStepDetailMutationService, 'validation_method_tree')
    def test_recording_rejects_empty_element_name(self, method_tree):
        method_tree.return_value = [{
            'value': 'w_click',
            'parameter': [{'f': 'locating', 'd': True}],
        }]
        page = SimpleNamespace(
            project_product=SimpleNamespace(ui_client_type=0),
            project_product_id=1,
        )

        with self.assertRaisesRegex(AutoUiError, '录制元素名称不能为空'):
            PageStepRecordingService._detail_payload(
                page,
                {
                    'action': 'click',
                    'name': '',
                    'detail': {'type': 0, 'ope_key': 'w_click', 'ope_value': []},
                    'element': {
                        'locators': [{'exp': 2, 'loc': 'get_by_text("提交")'}],
                    },
                },
                1,
                4,
            )

    def test_recording_rejects_empty_node_list(self):
        serializer = UiPageStepRecordingCommitSerializer(data={
            'page_id': 12,
            'name': '空录制',
            'nodes': [],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('nodes', serializer.errors)

    @patch('src.apps.auto_ui.services.page_step_recording.PageElement.objects.create')
    @patch('src.apps.auto_ui.services.page_step_recording.PageElement.objects.filter')
    def test_recording_uses_inline_element_name_when_creating_element(
            self,
            filter_element,
            create_element,
    ):
        filter_element.return_value.first.return_value = None

        PageStepRecordingService._resolve_element(
            SimpleNamespace(id=12),
            {
                'name': '提交审批按钮',
                'category': '填写订单信息',
                'element': {
                    'accessible_name': '提交',
                    'locators': [{'exp': 2, 'loc': 'get_by_text("提交")'}],
                },
            },
            4,
            'w_click',
            [],
        )

        create_data = create_element.call_args.kwargs
        self.assertEqual(create_data['name'], '提交审批按钮')
        self.assertEqual(create_data['category'], '填写订单信息')
        self.assertEqual(create_data['prompt'], '提交审批按钮')

    @patch('src.apps.auto_ui.services.page_step_recording.PageElement.objects.create')
    @patch('src.apps.auto_ui.services.page_step_recording.PageElement.objects.filter')
    def test_recording_defaults_new_element_category_to_uncategorized(
            self,
            filter_element,
            create_element,
    ):
        filter_element.return_value.first.return_value = None

        PageStepRecordingService._resolve_element(
            SimpleNamespace(id=12),
            {
                'name': '提交审批按钮',
                'element': {
                    'locators': [{'exp': 2, 'loc': 'get_by_text("提交")'}],
                },
            },
            4,
            'w_click',
            [],
        )

        self.assertEqual(create_element.call_args.kwargs['category'], '未分类')


class FakeQuerySet(list):

    def order_by(self, *args):
        return self

    def update(self, **kwargs):
        return len(self)


class UiTestCaseParametrizeTests(SimpleTestCase):

    def test_environment_scope_defaults_to_common(self):
        service = TestCase(user_id=1, username='liqian', test_env=1)

        self.assertTrue(service._TestCase__matches_test_environment({}))
        self.assertTrue(service._TestCase__matches_test_environment({'test_envs': None}))
        self.assertTrue(service._TestCase__matches_test_environment({'test_envs': []}))
        self.assertTrue(service._TestCase__matches_test_environment({'test_envs': [1, 2]}))
        self.assertFalse(service._TestCase__matches_test_environment({'test_envs': [2]}))

    def test_environment_scope_schema_normalizes_null_to_common(self):
        custom = UiCaseFrontCustomSchema.model_validate({
            'key': 'token',
            'value': 'common',
            'test_envs': None,
        })
        suite = UiCaseParametrizeSuite.model_validate({
            'name': '参数组1',
            'parametrize': [{'key': 'tenant', 'value': 'common', 'test_envs': None}],
        })

        self.assertEqual(custom.test_envs, [])
        self.assertEqual(suite.parametrize[0].test_envs, [])

    def make_case(self, parametrize, front_sql=None):
        return SimpleNamespace(
            id=1,
            name='允许空参数用例',
            status=None,
            save=lambda **_: None,
            front_custom=[],
            front_sql=front_sql or [],
            posterior_sql=[],
            parametrize=parametrize,
            module=SimpleNamespace(name='订单管理'),
            project_product=SimpleNamespace(id=1, name='示例项目'),
            case_people=SimpleNamespace(name='liqian'),
        )

    def run_case(self, case):
        step = SimpleNamespace(page_step=SimpleNamespace(id=1), switch_step_open_url=False)
        service = TestCase(user_id=1, username='liqian', test_env=1)

        with patch.object(ui_test_case_module.UiCase.objects, 'get', return_value=case), \
                patch.object(ui_test_case_module.UiCaseStepsDetailed.objects, 'filter',
                             return_value=FakeQuerySet([step])), \
                patch.object(service, '_TestCase__case_model', return_value=SimpleNamespace()), \
                patch.object(service, '_TestCase__socket_send'):
            return service.test_case(case_id=case.id)

    def test_case_parametrize_allows_empty_values(self):
        case = self.make_case([
            {
                'name': '参数组1',
                'parametrize': [
                    {'key': 'empty_text', 'value': ''},
                    {'key': 'null_value', 'value': None},
                    {'key': 'missing_value'},
                    {'key': 'zero_value', 'value': 0},
                    {'key': 'false_value', 'value': False},
                    {'key': 'empty_list', 'value': []},
                ],
            }
        ])

        self.assertIsNotNone(self.run_case(case))

    def test_case_parametrize_still_rejects_empty_key(self):
        case = self.make_case([{'name': '参数组1', 'parametrize': [{'key': '', 'value': 'ok'}]}])

        with self.assertRaises(AutoUiError):
            self.run_case(case)

    def test_case_front_data_source_operation_does_not_require_cache_key(self):
        case = self.make_case(
            [],
            front_sql=[{
                'sql': 'UPDATE users SET enabled = 1 WHERE id = 1',
                'key_list': '',
                'datasource_alias': 1,
            }],
        )

        self.assertIsNotNone(self.run_case(case))

    def test_case_front_data_source_operation_still_requires_content(self):
        case = self.make_case(
            [],
            front_sql=[{'sql': '', 'key_list': 'user_id', 'datasource_alias': 1}],
        )

        with self.assertRaises(AutoUiError):
            self.run_case(case)


class UiCaseDataSourceOperationValidationTests(SimpleTestCase):

    @staticmethod
    def alias(*, alias_id=9, project_product_id=22, status=1, db_type=0):
        return SimpleNamespace(
            id=alias_id,
            project_product_id=project_product_id,
            status=status,
            db_type=db_type,
        )

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_front_relational_operation_accepts_string(self, filter_alias):
        filter_alias.return_value = [self.alias()]

        result = validate_data_source_items(
            [{
                'sql': 'SELECT id FROM users LIMIT 1',
                'key_list': 'user_id',
                'datasource_alias': 9,
            }],
            UiCaseFrontSqlSchema,
            '前置数据库操作',
            22,
        )

        self.assertEqual(result[0]['sql'], 'SELECT id FROM users LIMIT 1')
        self.assertEqual(result[0]['test_envs'], [])

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_front_operation_preserves_selected_environments(self, filter_alias):
        filter_alias.return_value = [self.alias()]

        result = validate_data_source_items(
            [{
                'sql': 'SELECT 1',
                'datasource_alias': 9,
                'test_envs': [1, 2, 1],
            }],
            UiCaseFrontSqlSchema,
            '前置数据库操作',
            22,
        )

        self.assertEqual(result[0]['test_envs'], [1, 2])

    def test_front_operation_rejects_invalid_environment(self):
        with self.assertRaisesMessage(serializers.ValidationError, '包含无效执行环境'):
            validate_data_source_items(
                [{'sql': 'SELECT 1', 'datasource_alias': 9, 'test_envs': [999]}],
                UiCaseFrontSqlSchema,
                '前置数据库操作',
                22,
            )

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_posterior_redis_operation_rejects_json(self, filter_alias):
        filter_alias.return_value = [self.alias(db_type=10)]

        with self.assertRaisesMessage(AutoUiError, 'Redis执行内容必须是非空字符串'):
            validate_data_source_items(
                [{'sql': {'command': 'DEL user:1'}, 'datasource_alias': 9}],
                UiCasePosteriorSqlSchema,
                '后置数据库操作',
                22,
            )

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_front_elasticsearch_operation_accepts_standard_json(self, filter_alias):
        filter_alias.return_value = [self.alias(db_type=20)]

        result = validate_data_source_items(
            [{
                'sql': {'index': 'orders', 'query': {'match_all': {}}},
                'key_list': 'orders',
                'datasource_alias': 9,
            }],
            UiCaseFrontSqlSchema,
            '前置数据库操作',
            22,
        )

        self.assertEqual(result[0]['sql']['index'], 'orders')

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_front_operation_rejects_other_product_alias(self, filter_alias):
        filter_alias.return_value = [self.alias(project_product_id=23)]

        with self.assertRaisesMessage(AutoUiError, '不属于当前项目产品'):
            validate_data_source_items(
                [{'sql': 'SELECT 1', 'datasource_alias': 9}],
                UiCaseFrontSqlSchema,
                '前置数据库操作',
                22,
            )

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_front_operation_rejects_disabled_alias(self, filter_alias):
        filter_alias.return_value = [self.alias(status=0)]

        with self.assertRaisesMessage(AutoUiError, '逻辑数据源已停用'):
            validate_data_source_items(
                [{'sql': 'SELECT 1', 'datasource_alias': 9}],
                UiCaseFrontSqlSchema,
                '前置数据库操作',
                22,
            )


class UiStepDebugControlTests(SimpleTestCase):

    def test_frontend_debug_control_defaults(self):
        serializer = UiStepDebugControlSerializer(data={})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {
            'close_after_execution': False,
            'before_wait_seconds': 1,
            'after_wait_seconds': 1,
            'close_live_after_execution': False,
        })

    def test_frontend_debug_control_accepts_current_request_values(self):
        serializer = UiStepDebugControlSerializer(data={
            'close_after_execution': 'true',
            'before_wait_seconds': '3',
            'after_wait_seconds': '5',
            'close_live_after_execution': 'false',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['before_wait_seconds'], 3)
        self.assertEqual(serializer.validated_data['after_wait_seconds'], 5)
        self.assertTrue(serializer.validated_data['close_after_execution'])
        self.assertFalse(serializer.validated_data['close_live_after_execution'])

    def test_frontend_debug_control_accepts_selected_detail_id(self):
        serializer = UiStepDebugControlSerializer(data={'page_step_detail_id': '38'})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['page_step_detail_id'], 38)

    def test_selected_detail_debug_returns_single_step_message(self):
        request = Request(
            APIRequestFactory().get(
                '/api/ui/page/steps/test',
                {
                    'page_step_id': 8,
                    'te': 1,
                    'page_step_detail_id': 38,
                },
            )
        )
        request._user = {'id': 1, 'username': 'maopeng'}
        result = SimpleNamespace(model_dump=lambda: {'id': 8})

        with patch(
                'src.apps.auto_ui.api.views.ui_page_steps.TestCase'
        ) as test_case_class:
            test_case_class.return_value.test_steps.return_value = result
            response = PageStepsViews().ui_steps_run(request)

        self.assertEqual(response.data['code'], 200)
        self.assertEqual(
            response.data['msg'],
            '单步调试触发成功，正在当前实时浏览器中执行所选节点',
        )

    def test_frontend_debug_control_returns_parameter_error_for_invalid_detail_id(self):
        request = Request(
            APIRequestFactory().get(
                '/api/ui/page/steps/test',
                {
                    'page_step_id': 8,
                    'te': 1,
                    'page_step_detail_id': 'undefined',
                },
            )
        )

        response = PageStepsViews().ui_steps_run(request)

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '页面步骤调试参数不正确')
        self.assertIn('page_step_detail_id', response.data['data'])

    def test_selected_detail_debug_builds_single_node_runtime_model(self):
        service = TestCase(user_id=1, username='liqian', test_env=1)
        selected = SimpleNamespace(id=38, type=5)
        page_steps_model = SimpleNamespace(
            project_product=3,
            element_list=[
                SimpleNamespace(id=37, type=0),
                selected,
            ],
            flow_data=SimpleNamespace(id=37),
        )

        with patch.object(service, 'debug_steps_model', return_value=page_steps_model) as debug_steps_model, \
                patch.object(service, '_TestCase__ui_auth_cache', return_value=None), \
                patch.object(service, '_TestCase__socket_send') as socket_send:
            result = service.test_steps(8, page_step_detail_id=38)

        debug_steps_model.assert_called_once_with(8, page_step_detail_id=38)
        self.assertEqual(result.element_list, [selected])
        self.assertEqual(result.flow_data.id, 38)
        self.assertEqual(result.flow_data.type, 5)
        self.assertEqual(result.flow_data.children, [])
        socket_send.assert_called_once()


class UiOpenStepBrowserSerializerTests(SimpleTestCase):

    def test_accepts_test_environment_zero(self):
        serializer = UiOpenStepBrowserSerializer(data={
            'page_step_id': 8,
            'test_env': 0,
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['test_env'], 0)

    def test_invalid_environment_returns_parameter_error(self):
        request = SimpleNamespace(data={
            'page_step_id': 8,
            'test_env': 999,
        })

        response = PageStepsViews().open_browser(request)

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '打开页面步骤浏览器参数不正确')
        self.assertIn('test_env', response.data['data'])


class UiStepFlowDraftTests(SimpleTestCase):

    def test_disconnected_configured_nodes_are_kept_in_canvas_draft(self):
        flow_data = {
            'nodes': [
                {'id': 'node-1', 'config': {'id': 31}},
                {'id': 'node-2', 'config': {'id': 32}},
                {'id': 'node-3', 'config': {'id': None}},
            ],
            'edges': [],
        }

        self.assertEqual(PageStepFlowService.configured_detail_ids(flow_data), {31, 32})

    def test_stale_canvas_save_cannot_clear_saved_node_config(self):
        serializer = PageStepsSerializers()
        serializer.instance = SimpleNamespace(flow_data={
            'nodes': [
                {'id': 'condition-1', 'type': 4, 'config': {'id': 64}},
            ],
            'edges': [],
        })

        normalized = serializer.validate_flow_data({
            'nodes': [
                {'id': 'condition-1', 'type': 4, 'config': {}},
            ],
            'edges': [],
        })

        self.assertEqual(normalized['nodes'][0]['config']['id'], 64)

    def test_canvas_save_does_not_restore_config_for_deleted_node(self):
        serializer = PageStepsSerializers()
        serializer.instance = SimpleNamespace(flow_data={
            'nodes': [
                {'id': 'condition-1', 'type': 4, 'config': {'id': 64}},
            ],
            'edges': [],
        })

        normalized = serializer.validate_flow_data({'nodes': [], 'edges': []})

        self.assertEqual(normalized['nodes'], [])

    def test_condition_method_defers_expect_value_to_branch_node(self):
        method = {
            'parameter': [
                {'f': 'actual', 'd': False},
                {'f': 'expect', 'd': True},
            ],
        }

        PageStepDetailMutationService.validate_ope_value(
            method,
            [],
            deferred_fields={'expect'},
        )

    def test_regular_assertion_still_requires_expect_value(self):
        method = {'parameter': [{'f': 'expect', 'd': True}]}

        with self.assertRaises(AutoUiError):
            PageStepDetailMutationService.validate_ope_value(method, [])

    def test_condition_payload_accepts_expect_from_later_branch(self):
        method_tree = [{
            'value': 'page_contains_text',
            'parameter': [{'f': 'expect', 'd': True}],
        }]

        with patch.object(
                PageStepDetailMutationService,
                'validation_method_tree',
                return_value=method_tree,
        ):
            PageStepDetailMutationService.validate_detail_payload({
                'type': 4,
                'ope_key': 'page_contains_text',
                'ope_value': [],
                'condition_value': None,
            })

    def test_data_source_step_requires_logical_datasource(self):
        with self.assertRaisesMessage(AutoUiError, '必须选择逻辑数据源'):
            PageStepDetailMutationService.validate_detail_payload({
                'type': 2,
                'sql_execute': [{'sql': 'select 1', 'key_list': 'value'}],
            })

    def test_data_source_step_accepts_json_operation(self):
        PageStepDetailMutationService.validate_detail_payload({
            'type': 2,
            'sql_execute': [{
                'datasource_alias': 9,
                'sql': {'index': 'orders', 'query': {'match_all': {}}},
                'key_list': 'order_no',
            }],
        })

    def test_sql_assertion_requires_logical_datasource(self):
        method_tree = [{
            'value': 'assert_sql_count',
            'parameter': [
                {'f': 'actual', 'd': True},
                {'f': 'expect', 'd': True},
            ],
        }]

        with patch.object(
                PageStepDetailMutationService,
                'validation_method_tree',
                return_value=method_tree,
        ), self.assertRaisesMessage(AutoUiError, 'SQL断言必须选择逻辑数据源'):
            PageStepDetailMutationService.validate_detail_payload({
                'type': 1,
                'ope_key': 'assert_sql_count',
                'ope_value': [
                    {'f': 'actual', 'v': 'select 1'},
                    {'f': 'expect', 'v': '1'},
                ],
            }, project_product_id=22)

    @patch('src.apps.data_factory.models.DataFactoryDatasourceAlias.objects.filter')
    def test_sql_assertion_accepts_current_product_relational_datasource(self, filter_alias):
        filter_alias.return_value.first.return_value = SimpleNamespace(
            project_product_id=22,
            status=1,
            db_type=0,
        )
        method_tree = [{
            'value': 'assert_sql_count',
            'parameter': [
                {'f': 'actual', 'd': True},
                {'f': 'expect', 'd': True},
            ],
        }]

        with patch.object(
                PageStepDetailMutationService,
                'validation_method_tree',
                return_value=method_tree,
        ):
            PageStepDetailMutationService.validate_detail_payload({
                'type': 1,
                'ope_key': 'assert_sql_count',
                'ope_value': [
                    {'f': 'actual', 'v': 'select 1'},
                    {'f': 'expect', 'v': '1'},
                    {'f': 'datasource_alias', 'v': 9},
                ],
            }, project_product_id=22)

    def test_duplicate_node_keeps_all_business_configuration(self):
        source = SimpleNamespace(
            type=4,
            ele_name_id=17,
            step_sort=3,
            ope_key='page_contains_text',
            ope_value=[{'f': 'expect', 'v': '接受修订'}],
            sql_execute=None,
            key_list=None,
            sql=None,
            custom=None,
            key=None,
            value=None,
            condition_value={'expect': '接受修订'},
            func=None,
        )

        values = PageStepDetailMutationService.clone_detail_values(source)

        self.assertEqual(values['ele_name_id'], 17)
        self.assertEqual(values['condition_value'], {'expect': '接受修订'})
        self.assertEqual(values['ope_value'], [{'f': 'expect', 'v': '接受修订'}])
        self.assertIsNot(values['condition_value'], source.condition_value)

    def test_step_asset_contains_complete_page_and_step_context(self):
        project = SimpleNamespace(id=1, name='示例项目')
        product = SimpleNamespace(id=2, name='主服务', project=project)
        parent_module = SimpleNamespace(name='任务中心', parent=None)
        module = SimpleNamespace(id=3, name='待办详情', parent=parent_module)
        page = SimpleNamespace(id=4, name='任务中心待办详情', url='/task/detail')
        step = SimpleNamespace(
            id=5,
            name='打开待办详情',
            page_id=page.id,
            page=page,
            module_id=module.id,
            module=module,
            project_product=product,
        )

        option = PageStepAssetService._step_option(step)

        self.assertEqual(option['step_name'], '打开待办详情')
        self.assertEqual(option['page_name'], '任务中心待办详情')
        self.assertEqual(option['module_path'], '任务中心 / 待办详情')
        self.assertEqual(option['product_path'], '示例项目 / 主服务')


class UiAuthConfigSerializerTests(SimpleTestCase):

    def test_environment_is_required(self):
        serializer = UiAuthConfigSerializers(data={})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors['test_env'][0]), '请选择测试环境')

    def test_environment_does_not_accept_null(self):
        serializer = UiAuthConfigSerializers(data={'test_env': None})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(str(serializer.errors['test_env'][0]), '请选择测试环境')


class UiCaseRuntimeAuditTests(SimpleTestCase):

    @patch('src.apps.auto_ui.services.test_report_writing.ExecutionResultService.save_result')
    @patch('src.apps.auto_ui.services.test_report_writing.UiCase.objects.get')
    def test_case_result_does_not_touch_content_update_time(self, get_mock, save_result_mock):
        case = SimpleNamespace(id=15, status=None, save=Mock())
        get_mock.return_value = case
        result = SimpleNamespace(
            id=15,
            status=1,
            test_env=0,
            error_message=None,
            execution_id='execution-15',
            steps=[],
            data_factory_auto_cleanup_execution_ids=[],
            model_dump=lambda: {'id': 15, 'status': 1},
        )

        TestReportWriting.update_test_case(result)

        case.save.assert_called_once_with(update_fields=['status'])
        save_result_mock.assert_called_once()

    @patch('src.apps.auto_ui.services.test_report_writing.cache.set')
    @patch('src.apps.auto_ui.services.test_report_writing.transaction.atomic')
    @patch('src.apps.auto_ui.services.test_report_writing.ExecutionResultService.save_result')
    @patch('src.apps.auto_ui.services.test_report_writing.UiCaseStepsDetailed.objects.select_for_update')
    @patch('src.apps.auto_ui.services.test_report_writing.PageSteps.objects.select_for_update')
    def test_case_step_result_updates_page_step_status_and_latest_result(
            self,
            page_step_select_for_update,
            case_step_select_for_update,
            save_result_mock,
            _atomic_mock,
            _cache_set_mock,
    ):
        page_step = SimpleNamespace(id=7, status=0, save=Mock())
        page_step_select_for_update.return_value.filter.return_value.first.return_value = page_step
        case_step = SimpleNamespace(status=0, error_message='old', save=Mock())
        case_step_select_for_update.return_value.get.return_value = case_step
        result = SimpleNamespace(
            id=7,
            name='百度搜索',
            case_step_details_id=12,
            is_auth_step=False,
            status=1,
            error_message=None,
            test_env=2,
            execution_id='execution-7',
            slot_id=None,
            workspace_id=None,
            progress_sequence=0,
            element_result_list=[],
            model_dump=lambda: {'id': 7, 'status': 1},
        )

        TestReportWriting.update_step(result)

        self.assertEqual(page_step.status, 1)
        page_step.save.assert_called_once_with(update_fields=['status'])
        self.assertEqual(case_step.status, 1)
        self.assertIsNone(case_step.error_message)
        case_step.save.assert_called_once_with(update_fields=['status', 'error_message'])
        save_result_mock.assert_called_once()
        self.assertEqual(
            save_result_mock.call_args.kwargs['target_type'],
            'ui_page_step',
        )


class UiElementAiCandidateTests(SimpleTestCase):

    def test_rejects_unverified_candidate(self):
        self.assertEqual(
            ElementAiService._candidate_reject_reason({'verified': False, 'count': 1}),
            '候选定位器未通过浏览器验证',
        )

    def test_rejects_zero_match_candidate(self):
        self.assertEqual(
            ElementAiService._candidate_reject_reason({'verified': True, 'count': 0}),
            '候选定位器匹配数量小于1',
        )

    def test_rejects_multi_match_without_sub(self):
        self.assertEqual(
            ElementAiService._candidate_reject_reason({'verified': True, 'count': 119, 'sub': None}),
            '候选定位器匹配到多个元素且未指定下标，匹配数量：119',
        )

    def test_allows_unique_or_indexed_candidate(self):
        self.assertIsNone(ElementAiService._candidate_reject_reason({'verified': True, 'count': 1}))
        self.assertIsNone(ElementAiService._candidate_reject_reason({'verified': True, 'count': 119, 'sub': 1}))

    def test_auto_apply_rejects_multi_match_without_sub(self):
        record = SimpleNamespace(
            element=SimpleNamespace(),
            status=3,
            confidence=100,
            candidates=[{'verified': True, 'count': 119, 'sub': None, 'final_score': 100}],
        )

        with patch.object(ElementAiService, '_update_element_heal_status') as update_status, \
                patch.object(ElementAiService, '_apply_record_candidate') as apply_candidate:
            self.assertFalse(ElementAiService._auto_apply_record(record, 0))
            update_status.assert_called_once_with(record.element, record.status)
            apply_candidate.assert_not_called()

    def test_auto_apply_rejects_low_score_candidate(self):
        record = SimpleNamespace(
            element=SimpleNamespace(),
            status=3,
            confidence=0,
            candidates=[{'verified': True, 'count': 1, 'sub': None, 'final_score': 70}],
        )

        with patch.object(ElementAiService, '_update_element_heal_status') as update_status, \
                patch.object(ElementAiService, '_apply_record_candidate') as apply_candidate:
            self.assertFalse(ElementAiService._auto_apply_record(record, 0))
            update_status.assert_called_once_with(record.element, record.status)
            apply_candidate.assert_not_called()

    def test_auto_apply_accepts_high_score_unique_candidate(self):
        record = SimpleNamespace(
            element=SimpleNamespace(),
            status=3,
            confidence=0,
            candidates=[{
                'verified': True,
                'count': 1,
                'sub': None,
                'final_score': 90,
                'semantic_score': 100,
                'stability_score': 90,
                'operation_compatible': True,
                'auto_apply_operation_compatible': True,
                'consecutive_passes': 2,
                'stable_context': True,
                'auto_apply_eligible': True,
            }],
        )

        with patch.object(ElementAiService, '_update_element_heal_status') as update_status, \
                patch.object(ElementAiService, '_apply_record_candidate') as apply_candidate:
            self.assertTrue(ElementAiService._auto_apply_record(record, 0))
            update_status.assert_not_called()
            apply_candidate.assert_called_once_with(record, 0, 1, None, status=6)

    def test_auto_apply_rejects_candidate_without_strict_gate(self):
        record = SimpleNamespace(
            element=SimpleNamespace(),
            status=3,
            confidence=100,
            candidates=[{
                'verified': True,
                'count': 1,
                'final_score': 99,
                'semantic_score': 100,
                'stability_score': 90,
                'operation_compatible': True,
                'auto_apply_operation_compatible': True,
                'consecutive_passes': 1,
                'stable_context': True,
                'auto_apply_eligible': False,
            }],
        )

        with patch.object(ElementAiService, '_update_element_heal_status') as update_status, \
                patch.object(ElementAiService, '_apply_record_candidate') as apply_candidate:
            self.assertFalse(ElementAiService._auto_apply_record(record, 0))
            update_status.assert_called_once_with(record.element, record.status)
            apply_candidate.assert_not_called()

    def test_server_snapshot_sanitizer_redacts_browser_data(self):
        value = ElementAiDataSanitizer.snapshot({
            'url': 'https://example.test/page?token=secret&id=123',
            'element_value': 'password-value',
            'element_attributes': {'data-token': 'secret', 'aria-label': '账号'},
            'outer_html': '<input value="password-value"> user@example.com',
            'parent_html': 'Authorization=Bearer abcdefghijklmnop',
            'nearby_html': '<textarea>private</textarea>',
        })
        self.assertNotIn('secret', value['url'])
        self.assertEqual(value['element_value'], '')
        self.assertNotIn('data-token', value['element_attributes'])
        self.assertNotIn('password-value', value['outer_html'])
        self.assertNotIn('user@example.com', value['outer_html'])
        self.assertNotIn('abcdefghijklmnop', value['parent_html'])
        self.assertNotIn('private', value['nearby_html'])

    def test_server_candidate_sanitizer_preserves_locator_and_redacts_diagnostics(self):
        locator = 'get_by_text("订单 1234567890123456")'
        value = ElementAiDataSanitizer.locator_candidates([{
            'loc': locator,
            'reason': 'token=super-secret',
            'element_text': 'user@example.com',
            'count': 1,
        }])
        self.assertEqual(value[0]['loc'], locator)
        self.assertNotIn('super-secret', value[0]['reason'])
        self.assertNotIn('user@example.com', value[0]['element_text'])
        self.assertEqual(value[0]['count'], 1)

    def test_server_runtime_sanitizer_redacts_text_but_keeps_executable_locator(self):
        locator = 'get_by_role("button", name="订单 1234567890123456")'
        value = ElementAiDataSanitizer.runtime_snapshot({
            'page_url': 'https://example.test/page?token=super-secret',
            'access_token': 'super-secret',
            'error_message': 'Authorization=Bearer abcdefghijklmnop',
            'locator_engine': {'selected_loc': locator, 'token': 'super-secret'},
            'elements': [{
                'loc': locator,
                'element_text': 'user@example.com',
                'text_snippets': ['13800138000'],
            }],
        })
        self.assertNotIn('super-secret', value['page_url'])
        self.assertEqual(value['access_token'], '[REDACTED]')
        self.assertNotIn('abcdefghijklmnop', value['error_message'])
        self.assertEqual(value['locator_engine']['selected_loc'], locator)
        self.assertEqual(value['locator_engine']['token'], '[REDACTED]')
        self.assertEqual(value['elements'][0]['loc'], locator)
        self.assertNotIn('user@example.com', value['elements'][0]['element_text'])
        self.assertNotIn('13800138000', value['elements'][0]['text_snippets'][0])

    def test_server_runtime_sanitizer_formats_iso_checked_time(self):
        value = ElementAiDataSanitizer.runtime_snapshot({
            'checked_time': '2026-08-10T10:48:55.497787',
        })

        self.assertEqual(value['checked_time'], '2026-08-10 10:48:55')

    def test_page_element_serializers_format_latest_runtime_time(self):
        value = ElementAiDataSanitizer.datetime_text('2026-08-10T18:14:18.093853')

        self.assertEqual(value, '2026-08-10 18:14:18')
        self.assertEqual(
            PageElementSerializers().fields['latest_runtime_time'].format,
            '%Y-%m-%d %H:%M:%S',
        )
        self.assertEqual(
            PageElementSerializersC().fields['latest_runtime_time'].format,
            '%Y-%m-%d %H:%M:%S',
        )


class UiElementCheckTests(SimpleTestCase):

    @staticmethod
    def _element(expected_event=None):
        project_product = SimpleNamespace(id=7, name='WEB产品', ui_client_type=0)
        page = SimpleNamespace(
            id=48,
            name='订单页面',
            url='https://example.test/contracts',
            project_product=project_product,
            project_product_id=7,
        )
        return SimpleNamespace(
            id=15,
            name='适用部门',
            category='订单弹窗',
            expected_event=expected_event or {},
            page=page,
            exp=2,
            loc='get_by_role("combobox")',
            sub=None,
            exp2=None,
            loc2=None,
            sub2=None,
            exp3=None,
            loc3=None,
            sub3=None,
            is_iframe=0,
            prompt='适用部门',
            sleep=None,
            ai_heal_status=1,
        )

    def test_description_only_locator_uses_empty_placeholder_defaults(self):
        locator = UiElementLocator(
            prompt='创建订单弹窗中的订单名称输入框',
            is_placeholder=True,
        )

        self.assertIsNone(locator.exp)
        self.assertEqual(locator.loc, '')
        self.assertIsNone(locator.is_iframe)

    def test_check_element_without_fixed_locator_dispatches_description_placeholder(self):
        element = self._element()
        element.exp = None
        element.loc = None
        service = TestCase(user_id=1, username='mango', test_env=2)

        with patch.object(ui_test_case_module.PageElement.objects, 'select_related',
                          return_value=SimpleNamespace(get=lambda **_: element)), \
                patch.object(service, '_TestCase__cache_snapshot_baselines'), \
                patch.object(service, '_TestCase__should_collect_snapshot', return_value=False), \
                patch.object(service, '_TestCase__environment_config', return_value={
                    'id': 9,
                    'test_object_value': 'https://example.test',
                    'db_c_status': False,
                    'db_rud_status': False,
                }), \
                patch.object(service, '_TestCase__public_data', return_value=[]), \
                patch.object(service, '_TestCase__ui_auth_cache', return_value=None), \
                patch.object(service, '_TestCase__socket_send'):
            result = service.check_element(15, 'description-only')

        locators = result.element_list[0].elements
        self.assertEqual(len(locators), 1)
        self.assertTrue(locators[0].is_placeholder)
        self.assertEqual(locators[0].loc, '')

    def test_case_step_without_fixed_locator_builds_description_placeholder(self):
        element = self._element()
        element.exp = None
        element.loc = None
        element.locator_version = 1
        element.frame_path = []
        step = SimpleNamespace(
            id=21,
            ele_name=element,
            type=ElementOperationEnum.OPE,
            ope_key='w_click',
            ope_value=[],
            sql_execute=None,
            custom=None,
            condition_value=None,
            func=None,
        )
        service = TestCase(user_id=1, username='mango', test_env=2)

        with patch.object(service, '_TestCase__should_collect_snapshot', return_value=False):
            result = service.element_model(step)

        self.assertEqual(len(result.elements), 1)
        self.assertTrue(result.elements[0].is_placeholder)
        self.assertEqual(result.elements[0].loc, '')

    def test_check_element_uses_expected_event_and_dispatches_check_protocol(self):
        element = self._element({
            'ope_key': 'w_input',
            'ope_value': [
                {'f': 'locating', 'd': False},
                {'f': 'input_value', 'd': True, 'v': '${{username}}'},
            ],
        })
        service = TestCase(user_id=1, username='mango', test_env=2, is_send=True)

        with patch.object(ui_test_case_module.PageElement.objects, 'select_related',
                          return_value=SimpleNamespace(get=lambda **_: element)), \
                patch.object(service, '_TestCase__cache_snapshot_baselines'), \
                patch.object(service, '_TestCase__should_collect_snapshot', return_value=False), \
                patch.object(service, '_TestCase__environment_config', return_value={
                    'id': 9,
                    'test_object_value': 'https://example.test',
                    'db_c_status': False,
                    'db_rud_status': False,
                }), \
                patch.object(service, '_TestCase__public_data', return_value=[]), \
                patch.object(service, '_TestCase__ui_auth_cache', return_value=None), \
                patch.object(service, '_TestCase__socket_send') as socket_send:
            result = service.check_element(15, 'check-001')

        self.assertEqual(result.check_id, 'check-001')
        self.assertEqual(result.element_list[0].ope_key, 'w_input')
        self.assertEqual(result.element_list[0].ope_value[1]['v'], '${{username}}')
        socket_send.assert_called_once()

    def test_check_element_without_expected_event_uses_non_mutating_probe(self):
        element = self._element()
        service = TestCase(user_id=1, username='mango', test_env=2)

        with patch.object(ui_test_case_module.PageElement.objects, 'select_related',
                          return_value=SimpleNamespace(get=lambda **_: element)), \
                patch.object(service, '_TestCase__cache_snapshot_baselines'), \
                patch.object(service, '_TestCase__should_collect_snapshot', return_value=True), \
                patch.object(service, '_TestCase__environment_config', return_value={
                    'id': 9,
                    'test_object_value': 'https://example.test',
                    'db_c_status': False,
                    'db_rud_status': False,
                }), \
                patch.object(service, '_TestCase__public_data', return_value=[]), \
                patch.object(service, '_TestCase__ui_auth_cache', return_value=None), \
                patch.object(service, '_TestCase__socket_send'):
            result = service.check_element(15, 'check-002')

        self.assertEqual(result.element_list[0].ope_key, 'w_get_text')
        self.assertTrue(result.element_list[0].collect_snapshot)

    def test_deep_check_dispatches_all_three_locator_slots_including_empty_slots(self):
        element = self._element()
        service = TestCase(user_id=1, username='mango', test_env=2)

        with patch.object(ui_test_case_module.PageElement.objects, 'select_related',
                          return_value=SimpleNamespace(get=lambda **_: element)), \
                patch.object(service, '_TestCase__cache_snapshot_baselines'), \
                patch.object(service, '_TestCase__should_collect_snapshot', return_value=False), \
                patch.object(service, '_TestCase__environment_config', return_value={
                    'id': 9,
                    'test_object_value': 'https://example.test',
                    'db_c_status': False,
                    'db_rud_status': False,
                }), \
                patch.object(service, '_TestCase__public_data', return_value=[]), \
                patch.object(service, '_TestCase__ui_auth_cache', return_value=None), \
                patch.object(service, '_TestCase__socket_send'):
            result = service.check_element(15, 'check-deep', check_mode='deep')

        locators = result.element_list[0].elements
        self.assertEqual(len(locators), 3)
        self.assertEqual([item.slot for item in locators], [1, 2, 3])
        self.assertFalse(locators[0].is_placeholder)
        self.assertTrue(locators[1].is_placeholder)
        self.assertTrue(locators[2].is_placeholder)

    def test_deep_check_replaces_temporary_variables_without_mutating_element(self):
        element = self._element()
        element.name = '订单-${{订单id}}'
        element.prompt = '查找 ${{订单名称}}'
        element.loc = '//*[@data-id="${{订单id}}"]'
        element.exp2 = 9
        element.loc2 = '[aria-label="${{str_random_string()}}"]'
        element.page.url = 'https://example.test/contracts/${{订单id}}'
        service = TestCase(user_id=1, username='mango', test_env=2)

        with patch.object(ui_test_case_module.PageElement.objects, 'select_related',
                          return_value=SimpleNamespace(get=lambda **_: element)), \
                patch.object(service, '_TestCase__cache_snapshot_baselines'), \
                patch.object(service, '_TestCase__should_collect_snapshot', return_value=False), \
                patch.object(service, '_TestCase__environment_config', return_value={
                    'id': 9,
                    'test_object_value': 'https://example.test',
                    'db_c_status': False,
                    'db_rud_status': False,
                }), \
                patch.object(service, '_TestCase__public_data', return_value=[]), \
                patch.object(service, '_TestCase__ui_auth_cache', return_value=None), \
                patch.object(service, '_TestCase__socket_send'):
            result = service.check_element(
                15,
                'check-variables',
                check_mode='deep',
                runtime_variables={
                    '订单id': 'C-100',
                    '订单名称': '销售订单',
                    'str_random_string()': '固定随机值',
                },
            )

        self.assertEqual(result.name, '订单页面')
        self.assertEqual(result.url, 'https://example.test/contracts/C-100')
        self.assertEqual(result.element_list[0].name, '订单-C-100')
        self.assertEqual(result.element_list[0].elements[0].loc, '//*[@data-id="C-100"]')
        self.assertEqual(result.element_list[0].elements[0].prompt, '查找 销售订单')
        self.assertEqual(result.element_list[0].elements[1].loc, '[aria-label="固定随机值"]')
        self.assertEqual(element.loc, '//*[@data-id="${{订单id}}"]')
        self.assertEqual(element.page.url, 'https://example.test/contracts/${{订单id}}')

    def test_deep_check_writes_verified_same_target_locator_to_exact_slot(self):
        saved_fields = []
        element = SimpleNamespace(
            exp=2,
            loc='get_by_text("提交")',
            sub=None,
            exp2=None,
            loc2=None,
            sub2=None,
            exp3=9,
            loc3='button.submit',
            sub3=None,
            latest_match_count=None,
            latest_element_text=None,
            latest_runtime_time=None,
            latest_runtime_snapshot={},
            save=lambda update_fields: saved_fields.append(tuple(update_fields)),
        )
        with patch.object(ElementAiService, '_element_payload', return_value={'id': 15}), \
                patch.object(ElementAiService, '_trim_json', side_effect=lambda value: value), \
                patch.object(ElementAiService, '_latest_runtime_element', return_value=None), \
                patch.object(ui_test_case_module.PageElement.objects, 'get', return_value=element), \
                patch.object(
                    ui_test_case_module.PageElement.objects,
                    'filter',
                    return_value=SimpleNamespace(first=lambda: element),
                ):
            ElementAiService.save_check_result({
                'element_id': 15,
                'check_id': 'check-deep',
                'check_mode': 'deep',
                'selected_result': {
                    'elements': [],
                    'locator_engine': {
                        'locator_updates': [{
                            'slot': 2,
                            'exp': 0,
                            'loc': '//button[normalize-space()="提交"]',
                            'sub': None,
                            'same_target': True,
                        }],
                    },
                },
            })

            self.assertIsNone(element.loc2)
            ElementAiService._apply_locator_updates(15, {
                'check_mode': 'deep',
                'selected_result': element.latest_runtime_snapshot['selected_result'],
            })

        self.assertEqual(element.exp2, 0)
        self.assertEqual(element.loc2, '//button[normalize-space()="提交"]')
        self.assertIn(('exp2', 'loc2', 'sub2', 'update_time'), saved_fields)

    def test_runtime_locator_persistence_rejects_temporary_snapshot_ref(self):
        saved_fields = []
        element = SimpleNamespace(
            locator_version=4,
            exp=9,
            loc='[data-mango-healing-ref="oldshot123:e2"]',
            sub=None,
            exp2=None,
            loc2=None,
            sub2=None,
            exp3=None,
            loc3=None,
            sub3=None,
            save=lambda update_fields: saved_fields.extend(update_fields),
        )

        persisted, reason = ElementAiService._persist_runtime_locator_updates(
            element,
            1,
            {
                'temporary_heal_used': True,
                'base_locator_version': 4,
                'locator_updates': [{
                    'exp': 1,
                    'loc': '[data-mango-healing-ref="snapshot1234:e2"]',
                    'strategy': 'snapshot_ref_temporary',
                    'frame_index': 0,
                    'same_target': True,
                    'verified': True,
                }],
            },
        )

        self.assertFalse(persisted)
        self.assertEqual(reason, 'no_persistable_verified_locator_transient_removed')
        self.assertIsNone(element.loc)
        self.assertEqual(element.locator_version, 5)
        self.assertIn('locator_version', saved_fields)

    def test_deep_check_fills_empty_third_locator_slot(self):
        saved_fields = []
        element = SimpleNamespace(
            exp=2,
            loc='locator("#kw")',
            sub=None,
            exp2=0,
            loc2='//textarea[@id="chat-textarea"]',
            sub2=None,
            exp3=None,
            loc3=None,
            sub3=None,
            latest_match_count=None,
            latest_element_text=None,
            latest_runtime_time=None,
            latest_runtime_snapshot={},
            save=lambda update_fields: saved_fields.append(tuple(update_fields)),
        )
        with patch.object(ElementAiService, '_element_payload', return_value={'id': 1}), \
                patch.object(ElementAiService, '_trim_json', side_effect=lambda value: value), \
                patch.object(ElementAiService, '_latest_runtime_element', return_value=None), \
                patch.object(ui_test_case_module.PageElement.objects, 'get', return_value=element), \
                patch.object(
                    ui_test_case_module.PageElement.objects,
                    'filter',
                    return_value=SimpleNamespace(first=lambda: element),
                ):
            ElementAiService.save_check_result({
                'element_id': 1,
                'check_id': 'check-fill-third',
                'check_mode': 'deep',
                'selected_result': {
                    'elements': [],
                    'locator_engine': {
                        'locator_updates': [{
                            'slot': 3,
                            'exp': 2,
                            'loc': 'get_by_role("textbox", name="搜索")',
                            'sub': None,
                            'same_target': True,
                        }],
                    },
                },
            })

            self.assertIsNone(element.loc3)
            ElementAiService._apply_locator_updates(1, {
                'check_mode': 'deep',
                'selected_result': element.latest_runtime_snapshot['selected_result'],
            })

        self.assertEqual(element.exp3, 2)
        self.assertEqual(element.loc3, 'get_by_role("textbox", name="搜索")')
        self.assertIn(('exp3', 'loc3', 'sub3', 'update_time'), saved_fields)

    def test_deep_check_apply_rejects_non_deep_task_result(self):
        with patch.object(
                ui_test_case_module.PageElement.objects,
                'filter',
                return_value=SimpleNamespace(first=lambda: SimpleNamespace()),
        ):
            with self.assertRaises(AutoUiError):
                ElementAiService._apply_locator_updates(1, {'check_mode': 'normal'})

    def test_deep_check_apply_rejects_unverified_locator_update(self):
        element = SimpleNamespace(
            latest_runtime_snapshot={
                'check_id': 'check-deep',
                'check_mode': 'deep',
                'selected_result': {
                    'locator_engine': {
                        'locator_updates': [{
                            'slot': 3,
                            'exp': 2,
                            'loc': 'get_by_role("textbox")',
                            'same_target': False,
                        }],
                    },
                },
            },
        )
        with patch.object(
                ui_test_case_module.PageElement.objects,
                'filter',
                return_value=SimpleNamespace(first=lambda: element),
        ):
            with self.assertRaisesRegex(AutoUiError, '没有可写入的定位组'):
                ElementAiService._apply_locator_updates(1, {
                    'check_mode': 'deep',
                    'selected_result': element.latest_runtime_snapshot['selected_result'],
                })

    def test_check_result_updates_runtime_fields_without_touching_config_time(self):
        saved_fields = []
        element = SimpleNamespace(
            latest_match_count=None,
            latest_element_text=None,
            latest_runtime_time=None,
            latest_runtime_snapshot={},
            save=lambda update_fields: saved_fields.extend(update_fields),
        )
        with patch.object(ElementAiService, '_element_payload', return_value={'id': 15}), \
                patch.object(ElementAiService, '_trim_json', side_effect=lambda value: value), \
                patch.object(ElementAiService, '_latest_runtime_element', return_value={
                    'ele_quantity': 1,
                    'element_text': '适用部门',
                }), \
                patch.object(ElementAiService, '_to_int', return_value=1), \
                patch.object(ElementAiService, '_trim', return_value='适用部门'), \
                patch.object(ui_test_case_module.PageElement.objects, 'get', return_value=element):
            ElementAiService.save_check_result({
                'element_id': 15,
                'check_id': 'check-003',
                'check_mode': 'deep',
                'selected_result': {
                    'elements': [],
                    'picture_name': '深度检测截图.jpg',
                    'picture_path': 'mango-file/uitest/screenshot/deep-check.jpg',
                    'locator_engine': {'screenshot_captured': True},
                },
            })

        self.assertNotIn('update_time', saved_fields)
        self.assertEqual(element.latest_match_count, 1)
        self.assertEqual(
            element.latest_runtime_snapshot['selected_result']['picture_path'],
            'mango-file/uitest/screenshot/deep-check.jpg',
        )
        self.assertTrue(
            element.latest_runtime_snapshot['selected_result']['locator_engine']['screenshot_captured']
        )
