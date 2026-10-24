import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest import skip
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.auto_api.api.serializers.api_case_detailed_parameter_mutation import (
    ApiCaseDetailedParameterSerializers,
)
from src.apps.auto_api.api.serializers.api_info_mutation import ApiInfoSerializers
from src.apps.auto_api.api.serializers.api_pulic import ApiPublicSerializers
from src.apps.auto_api.enums import ApiConfigObjectTypeEnum
from src.apps.auto_api.exceptions import (
    API_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
    API_CACHE_STEP_NOT_FOUND,
    API_TEST_ENVIRONMENT_USER_INVALID,
    AutoApiError,
    API_POST_FUNCTION_FAILED,
    API_CONCURRENCY_LIMIT_EXCEEDED,
)
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiInfo,
    ApiPublic,
)
from src.apps.auto_api.schemas.case_schema import ApiParametrizeSuite, validate_sql_item_list
from src.apps.auto_api.schemas.execution import ApiStepExecutionContext, ApiExecutionRequest, ApiExecutionResponse
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_api.services.base.api_base_test_setup.base_request import BaseRequest
from src.apps.auto_api.services.base.api_base_test_setup.request_body import prepare_request_body
from src.apps.auto_api.services.base.assertion_verification import ApiAssertionVerificationService
from src.apps.auto_api.services.base.case_base import CaseBase
from src.apps.auto_api.services.base.case_parameter import CaseParameter
from src.apps.auto_api.services.base.sql_environment import should_execute_sql
from src.apps.auto_api.services.config.version import ApiConfigSnapshotService, ApiConfigDiffService
from src.apps.auto_api.services.execution_trace.builder import ApiCaseExecutionTraceBuilder
from src.apps.auto_api.services.test_case.step_debug import ApiCaseStepDebugContextService
from src.apps.task_center.models import Tasks, TasksDetails, TimeTasks
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import (
    ProductModule,
    Project,
    ProjectProduct,
    TestSuite,
    TestSuiteDetails,
)
from src.apps.user.models import User
from src.common.responses.json_response import extract_jsonpath_value


class _RemovedApiConfigVersion:
    """仅供已跳过的旧版本测试完成模块加载；生产代码已不再使用该模型。"""

    OBJECT_TYPE_API_INFO = ApiConfigObjectTypeEnum.API_INFO.value
    OBJECT_TYPE_API_CASE = ApiConfigObjectTypeEnum.API_CASE.value
    objects = None


ApiConfigVersion = _RemovedApiConfigVersion


# Create your tests here.


class MyTestCase(TestCase):

    def test_user_info(self):
        url = "/api/case/api/info/run"
        response = self.client.get(url)
        print(response.json())


class ApiCaseExecutionTraceBuilderTests(SimpleTestCase):

    def test_build_nodes_keeps_parent_step_id(self):
        nodes = ApiCaseExecutionTraceBuilder.build_nodes([
            {
                'id': 10,
                'parent_step_id': None,
                'step_name': '第 1/50 轮',
                'step_type': 'retry_round',
                'status': 0,
                'duration_ms': 10000,
            },
            {
                'id': 11,
                'parent_step_id': 10,
                'step_name': '等待下次重试',
                'step_type': 'retry_wait',
                'status': 1,
                'duration_ms': 10000,
            },
        ])

        self.assertIsNone(nodes[0]['parent_step_id'])
        self.assertEqual(nodes[1]['parent_step_id'], '10')


class ApiCaseStepDebugExpirationTests(SimpleTestCase):

    def test_expiration_supports_naive_and_aware_datetimes(self):
        self.assertFalse(ApiCaseStepDebugContextService.is_expired(datetime.now().isoformat()))
        self.assertFalse(ApiCaseStepDebugContextService.is_expired(datetime.now().astimezone().isoformat()))
        self.assertTrue(ApiCaseStepDebugContextService.is_expired(
            (datetime.now().astimezone() - timedelta(hours=3)).isoformat()
        ))


class ApiCaseStepDebugContextTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='单步调试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='调试模块')
        self.user = User.objects.create(
            name='调试用户',
            username='api_step_debug_user',
            password='pwd',
            is_super_admin=True,
        )
        self.case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='创建启用删除链路',
            case_people=self.user,
            case_flow='',
        )
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='调试接口',
            url='/debug/resource',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )
        self.steps = []
        self.parameters = []
        for case_sort, name in enumerate(['创建数据', '启用数据', '删除数据'], start=1):
            step = ApiCaseDetailed.objects.create(
                case=self.case,
                api_info=self.api_info,
                case_sort=case_sort,
            )
            parameter = ApiCaseDetailedParameter.objects.create(
                case_detailed=step,
                name=name,
            )
            self.steps.append(step)
            self.parameters.append(parameter)

    def write_snapshot(
            self,
            index: int,
            *,
            context_id: str,
            snapshot_id: str,
            parent_snapshot_id: str | None,
            test_env: int = 0,
    ):
        step = self.steps[index]
        parameter = self.parameters[index]
        execution_context = ApiStepExecutionContext(
            context_id=context_id,
            snapshot_id=snapshot_id,
            parent_snapshot_id=parent_snapshot_id,
            case_id=self.case.id,
            case_detailed_id=step.id,
            case_sort=step.case_sort,
            test_env=test_env,
            user_id=self.user.id,
            trace_id=f'trace-{snapshot_id}',
            executed_at=timezone.now().isoformat(),
        ).model_dump()
        step.status = StatusEnum.SUCCESS.value
        step.save(update_fields=['status', 'update_time'])
        parameter.status = StatusEnum.SUCCESS.value
        parameter.result_data = {
            'status': StatusEnum.SUCCESS.value,
            'cache_data': {'resource_id': 100 + index, 'step': index + 1},
            'data_factory_cache_data': {'factory_step': index + 1},
            'execution_context': execution_context,
        }
        parameter.save(update_fields=['status', 'result_data', 'update_time'])

    def test_first_step_creates_fresh_context_without_previous_cache(self):
        state = ApiCaseStepDebugContextService.prepare(
            case_id=self.case.id,
            case_detailed_id=self.steps[0].id,
            test_env=0,
            user_id=self.user.id,
        )

        self.assertTrue(state.run_case_front)
        self.assertEqual(state.context_source, 'new')
        self.assertIsNone(state.parent_snapshot_id)
        self.assertEqual(state.cache_data, {})

    def test_second_step_restores_previous_step_cumulative_cache(self):
        self.write_snapshot(0, context_id='context-a', snapshot_id='snapshot-1', parent_snapshot_id=None)

        state = ApiCaseStepDebugContextService.prepare(
            case_id=self.case.id,
            case_detailed_id=self.steps[1].id,
            test_env=0,
            user_id=self.user.id,
            context_id='context-a',
        )

        self.assertFalse(state.run_case_front)
        self.assertEqual(state.parent_snapshot_id, 'snapshot-1')
        self.assertEqual(state.restored_from_step_id, self.steps[0].id)
        self.assertEqual(state.cache_data, {'resource_id': 100, 'step': 1})
        self.assertEqual(state.data_factory_cache_data, {'factory_step': 1})

    def test_debug_rejects_snapshot_from_another_environment(self):
        self.write_snapshot(0, context_id='context-a', snapshot_id='snapshot-1', parent_snapshot_id=None)

        with self.assertRaises(AutoApiError) as context:
            ApiCaseStepDebugContextService.prepare(
                case_id=self.case.id,
                case_detailed_id=self.steps[1].id,
                test_env=3,
                user_id=self.user.id,
                context_id='context-a',
            )

        self.assertEqual(context.exception.code, API_TEST_ENVIRONMENT_USER_INVALID.code)

    def test_rerunning_predecessor_invalidates_old_downstream_snapshot(self):
        self.write_snapshot(0, context_id='context-a', snapshot_id='snapshot-1', parent_snapshot_id=None)
        self.write_snapshot(1, context_id='context-a', snapshot_id='snapshot-2', parent_snapshot_id='snapshot-1')
        self.write_snapshot(0, context_id='context-a', snapshot_id='snapshot-1-new', parent_snapshot_id=None)

        with self.assertRaises(AutoApiError) as context:
            ApiCaseStepDebugContextService.prepare(
                case_id=self.case.id,
                case_detailed_id=self.steps[2].id,
                test_env=0,
                user_id=self.user.id,
                context_id='context-a',
            )

        self.assertEqual(context.exception.code, API_TEST_ENVIRONMENT_USER_INVALID.code)

    def test_debug_requires_successful_previous_step(self):
        with self.assertRaises(AutoApiError) as context:
            ApiCaseStepDebugContextService.prepare(
                case_id=self.case.id,
                case_detailed_id=self.steps[1].id,
                test_env=0,
                user_id=self.user.id,
            )

        self.assertEqual(context.exception.code, API_CACHE_STEP_NOT_FOUND.code)


class ApiInfoDuplicateValidationTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='重复校验项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='模块A')

    def make_payload(self, name='接口A'):
        return {
            'project_product': self.product.id,
            'module': self.module.id,
            'type': 1,
            'name': name,
            'url': '/ai/unbox-chat/message',
            'method': 1,
            'headers': None,
            'params': None,
            'protocol_type': 'http',
            'body_type': 'none',
            'body_config': None,
            'sse_config': None,
        }

    def test_api_info_rejects_duplicate_route_identity(self):
        ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='已有接口',
            url='/ai/unbox-chat/message',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )

        serializer = ApiInfoSerializers(data=self.make_payload('重复接口'))

        with self.assertRaises(AutoApiError):
            serializer.is_valid()

    def test_api_info_rejects_duplicate_route_identity_with_different_manage_type(self):
        ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            type=0,
            name='录制接口',
            url='/ai/unbox-chat/message',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )

        serializer = ApiInfoSerializers(data=self.make_payload('调试接口'))

        with self.assertRaises(AutoApiError):
            serializer.is_valid()

    def test_api_info_allows_updating_self(self):
        api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='已有接口',
            url='/ai/unbox-chat/message',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )

        serializer = ApiInfoSerializers(instance=api_info, data={'name': '改名'}, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)


class ApiPublicDuplicateValidationTests(SimpleTestCase):

    def setUp(self):
        self.product = SimpleNamespace(id=1)
        self.existing = SimpleNamespace(
            id=321,
            test_envs=[0, 3],
            key='access_token',
            value='token-value',
        )

    def make_payload(self, **overrides):
        payload = {
            'project_product': self.product,
            'test_envs': [0, 3],
            'type': 0,
            'name': '新变量',
            'key': 'access_token',
            'value': 'token-value',
            'status': 0,
        }
        payload.update(overrides)
        return payload

    def test_create_rejects_same_fields_when_environment_order_differs(self):
        serializer = ApiPublicSerializers()
        candidates = SimpleNamespace(only=lambda *args: [self.existing])

        with patch.object(ApiPublic.objects, 'filter', return_value=candidates):
            with self.assertRaises(AutoApiError) as context:
                serializer.validate(self.make_payload(test_envs=[3, 0]))

        self.assertIn(f'重复变量ID：{self.existing.id}', context.exception.msg)

    def test_create_allows_different_value(self):
        serializer = ApiPublicSerializers()
        candidates = SimpleNamespace(only=lambda *args: [self.existing])

        with patch.object(ApiPublic.objects, 'filter', return_value=candidates):
            attrs = serializer.validate(self.make_payload(value='other-token'))

        self.assertEqual(attrs['value'], 'other-token')


class ApiInfoBoundCaseTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='绑定用例项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='订单模块')
        self.owner = User.objects.create(name='负责人A', username='owner_a', password='pwd', is_super_admin=True)
        self.update_user = User.objects.create(name='更新人B', username='editor_b', password='pwd')
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='创建订单',
            url='/open-apis/contract/v1/contracts',
            method=1,
            headers=None,
            protocol_type='http',
            body_type='none',
        )
        other_api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='无关接口',
            url='/open-apis/contract/v1/other',
            method=0,
            headers=None,
            protocol_type='http',
            body_type='none',
        )
        self.case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='订单创建链路',
            case_people=self.owner,
            update_user=self.update_user,
            case_flow='',
        )
        first_step = ApiCaseDetailed.objects.create(
            case=self.case,
            api_info=self.api_info,
            update_user=self.update_user,
            case_sort=1,
            status=1,
        )
        second_step = ApiCaseDetailed.objects.create(
            case=self.case,
            api_info=self.api_info,
            case_sort=2,
            status=2,
        )
        unrelated_step = ApiCaseDetailed.objects.create(
            case=self.case,
            api_info=other_api_info,
            case_sort=3,
            status=2,
        )
        ApiCaseDetailedParameter.objects.create(case_detailed=first_step, name='新建订单')
        ApiCaseDetailedParameter.objects.create(case_detailed=second_step, name='提交订单')
        ApiCaseDetailedParameter.objects.create(case_detailed=unrelated_step, name='无关步骤')

    def test_get_api_info_bound_cases_returns_distinct_cases_for_current_api(self):
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(
            '/api/api/info/bound/cases',
            {'id': self.api_info.id},
            HTTP_AUTHORIZATION=token,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['code'], 200)
        self.assertEqual(body['totalSize'], 1)
        self.assertEqual(body['data'][0]['update_user_name'], '更新人B')
        self.assertEqual(
            [(item['case_id'], item['case_name']) for item in body['data']],
            [(self.case.id, '订单创建链路')],
        )


class ApiCaseScheduledTaskTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='定时任务筛选项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='订单模块')
        self.owner = User.objects.create(name='负责人B', username='owner_b', password='pwd', is_super_admin=True)
        self.bound_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='已绑定定时任务用例',
            case_people=self.owner,
            case_flow='',
        )
        self.unbound_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='未绑定定时任务用例',
            case_people=self.owner,
            case_flow='',
        )
        self.time_task = TimeTasks.objects.create(name='每日巡检', cron='0 8 * * *')
        self.task = Tasks.objects.create(
            project_product=self.product,
            module=self.module,
            test_env=1,
            name='生产巡检任务',
            case_people=self.owner,
            status=1,
            timing_strategy=self.time_task,
            is_notice=1,
            fail_notice=1,
        )
        self.task_detail = TasksDetails.objects.create(
            type=TestCaseTypeEnum.API.value,
            task=self.task,
            api_case=self.bound_case,
        )
        self.token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

    def test_filter_bound_api_cases(self):
        response = self.client.get(
            '/api/api/case',
            {'scheduled_task': 'bound', 'page': 1, 'pageSize': 20},
            HTTP_AUTHORIZATION=self.token,
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['code'], 200)
        self.assertEqual([item['id'] for item in body['data']], [self.bound_case.id])

    def test_filter_unbound_api_cases(self):
        response = self.client.get(
            '/api/api/case',
            {'scheduled_task': 'unbound', 'page': 1, 'pageSize': 20},
            HTTP_AUTHORIZATION=self.token,
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['code'], 200)
        self.assertEqual([item['id'] for item in body['data']], [self.unbound_case.id])

    def test_get_api_case_bound_tasks(self):
        response = self.client.get(
            '/api/api/case/bound/tasks',
            {'id': self.bound_case.id},
            HTTP_AUTHORIZATION=self.token,
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['code'], 200)
        self.assertEqual(body['totalSize'], 1)
        self.assertEqual(body['data'][0]['task_detail_id'], self.task_detail.id)
        self.assertEqual(body['data'][0]['task_id'], self.task.id)
        self.assertEqual(body['data'][0]['task_name'], '生产巡检任务')
        self.assertEqual(body['data'][0]['timing_strategy_name'], '每日巡检')
        self.assertEqual(body['data'][0]['cron'], '0 8 * * *')
        self.assertEqual(body['data'][0]['test_env'], 1)
        self.assertEqual(body['data'][0]['case_people_name'], '负责人B')
        self.assertEqual(body['data'][0]['status'], 1)
        self.assertEqual(body['data'][0]['is_notice'], 1)
        self.assertEqual(body['data'][0]['fail_notice'], 1)
        self.assertEqual(body['data'][0]['project_product_id'], self.product.id)
        self.assertEqual(body['data'][0]['module_id'], self.module.id)


class ApiCaseBatchExecutionTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='批量执行项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='批量执行模块')
        self.user = User.objects.create(
            name='批量执行用户',
            username='batch_execution_user',
            password='pwd',
            is_super_admin=True,
            selected_environment=0,
        )
        self.case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='批量执行用例',
            case_people=self.user,
            case_flow='',
        )
        self.token = jwt.encode({'id': self.user.id}, settings.SECRET_KEY, algorithm='HS256')

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_batch_execution_saves_name_and_concurrency_snapshot(self, _mock_limit):
        response = self.client.post(
            '/api/api/case/batch',
            {
                'case_id_list': [self.case.id],
                'test_env': 3,
                'execution_name': '订单主流程回归',
                'api_concurrency_limit': 2,
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        body = response.json()
        self.assertEqual(body['code'], 200)
        report = TestSuite.objects.get(id=body['data']['test_suite_id'])
        self.assertEqual(report.execution_name, '订单主流程回归')
        self.assertEqual(body['data']['test_env'], 3)
        self.assertEqual(report.test_env, 3)
        self.assertEqual(report.api_concurrency_limit, 2)
        self.assertFalse(
            TestSuiteDetails.objects.filter(test_suite=report).exclude(test_env=3).exists()
        )

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_batch_execution_uses_platform_limit_when_concurrency_is_empty(self, _mock_limit):
        response = self.client.post(
            '/api/api/case/batch',
            {
                'case_id_list': [self.case.id],
                'test_env': 0,
                'execution_name': '平台默认并发任务',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        body = response.json()
        self.assertEqual(body['code'], 200)
        report = TestSuite.objects.get(id=body['data']['test_suite_id'])
        self.assertEqual(body['data']['api_concurrency_limit'], 3)
        self.assertEqual(report.api_concurrency_limit, 3)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_batch_execution_rejects_over_limit_without_creating_report(self, _mock_limit):
        response = self.client.post(
            '/api/api/case/batch',
            {
                'case_id_list': [self.case.id],
                'test_env': 0,
                'execution_name': '超限任务',
                'api_concurrency_limit': 4,
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], API_CONCURRENCY_LIMIT_EXCEEDED[0])
        self.assertFalse(TestSuite.objects.exists())

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_batch_execution_requires_explicit_environment(self, _mock_limit):
        response = self.client.post(
            '/api/api/case/batch',
            {
                'case_id_list': [self.case.id],
                'execution_name': '未选择环境任务',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], API_TEST_ENVIRONMENT_EXECUTION_REQUIRED.code)
        self.assertFalse(TestSuite.objects.exists())


@skip('旧通用 ApiConfigVersion 已移除，差异脱敏测试由独立快照测试覆盖')
class ApiConfigDiffServiceTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='版本管理项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.module = ProductModule.objects.create(project_product=self.product, name='订单模块')
        self.owner = User.objects.create(
            name='版本负责人',
            username='version_owner',
            password='pwd',
            is_super_admin=True,
        )
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='创建订单',
            url='/open-apis/contract/v1/contracts',
            method=1,
            headers={'Authorization': 'Bearer old-token', 'X-Trace': 'old'},
            protocol_type='http',
            body_type='json',
            body_config={'json': {'contract_name': 'old'}},
            result_data={'json': {'access_token': 'unsafe'}},
        )
        self.case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='订单创建链路',
            case_people=self.owner,
            case_flow='',
        )
        self.step = ApiCaseDetailed.objects.create(
            case=self.case,
            api_info=self.api_info,
            case_sort=1,
            status=2,
        )
        self.parameter = ApiCaseDetailedParameter.objects.create(
            case_detailed=self.step,
            name='创建订单成功',
            body_config={'json': {'contract_name': 'old'}},
            result_data={'response': {'json': {'id': 1}}},
        )

    def test_record_api_info_update_stores_diff_and_masks_sensitive_values(self):
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(self.api_info).snapshot
        self.api_info.name = '创建订单-改名'
        self.api_info.headers = {'Authorization': 'Bearer new-token', 'X-Trace': 'new'}
        self.api_info.save()

        version = ApiConfigDiffService.record_instance_change(
            self.api_info,
            action='update',
            before_snapshot=before_snapshot,
            operator_id=self.owner.id,
            source='test',
            summary='接口改名',
        )

        self.assertEqual(version.object_type, ApiConfigVersion.OBJECT_TYPE_API_INFO)
        self.assertEqual(version.object_id, self.api_info.id)
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.operator_id, self.owner.id)
        self.assertEqual(version.before_snapshot['headers']['Authorization'], '***')
        self.assertEqual(version.after_snapshot['headers']['Authorization'], '***')
        self.assertNotIn('result_data', version.after_snapshot)
        self.assertIn('name', {item['path'] for item in version.diff})
        self.assertIn('headers.X-Trace', {item['path'] for item in version.diff})

    def test_record_change_keeps_semantic_secret_change_and_masks_persisted_audit_data(self):
        before_snapshot = {
            'project_product': self.product.id,
            'module': self.module.id,
            'body_config': {
                'fields': [
                    {'key': 'Authorization', 'value': 'Bearer before-value'},
                ],
            },
        }
        after_snapshot = {
            'project_product': self.product.id,
            'module': self.module.id,
            'body_config': {
                'fields': [
                    {'key': 'Authorization', 'value': 'Bearer after-value'},
                ],
            },
        }

        version = ApiConfigDiffService.record_change(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
            action='update',
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            source='test',
        )

        self.assertIsNotNone(version)
        version.refresh_from_db()
        self.assertEqual(version.before_snapshot['body_config']['fields'][0]['value'], '***')
        self.assertEqual(version.after_snapshot['body_config']['fields'][0]['value'], '***')
        diff_by_path = {item['path']: item for item in version.diff}
        self.assertIn('body_config.fields.0.value', diff_by_path)
        self.assertEqual(diff_by_path['body_config.fields.0.value']['before'], '***')
        self.assertEqual(diff_by_path['body_config.fields.0.value']['after'], '***')

    def test_record_instance_change_detects_semantic_secret_only_update(self):
        self.api_info.body_config = {
            'fields': [
                {'key': 'Authorization', 'value': 'Bearer captured-before'},
            ],
        }
        self.api_info.save(update_fields=['body_config'])
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(self.api_info).snapshot
        self.api_info.body_config = {
            'fields': [
                {'key': 'Authorization', 'value': 'Bearer captured-after'},
            ],
        }
        self.api_info.save(update_fields=['body_config'])

        version = ApiConfigDiffService.record_instance_change(
            self.api_info,
            action='update',
            before_snapshot=before_snapshot,
            source='test',
        )

        self.assertIsNotNone(version)
        self.assertEqual(version.before_snapshot['body_config']['fields'][0]['value'], '***')
        self.assertEqual(version.after_snapshot['body_config']['fields'][0]['value'], '***')
        self.assertIn('body_config.fields.0.value', {item['path'] for item in version.diff})

    def test_record_change_masks_semantic_secret_beneath_dotted_key(self):
        before_snapshot = {
            'payload.with.dot': [
                {'key': 'Authorization', 'value': 'dotted-before-value'},
            ],
            'normal.with.dot': [
                {'key': 'normal', 'value': 'normal-before-value'},
            ],
        }
        after_snapshot = {
            'payload.with.dot': [
                {'key': 'Authorization', 'value': 'dotted-after-value'},
            ],
            'normal.with.dot': [
                {'key': 'normal', 'value': 'normal-after-value'},
            ],
        }

        version = ApiConfigDiffService.record_change(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
            action='update',
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            source='test',
        )

        diff_by_path = {item['path']: item for item in version.diff}
        diff_item = diff_by_path['payload.with.dot.0.value']
        self.assertEqual(diff_item['before'], '***')
        self.assertEqual(diff_item['after'], '***')
        normal_diff_item = diff_by_path['normal.with.dot.0.value']
        self.assertEqual(normal_diff_item['before'], 'normal-before-value')
        self.assertEqual(normal_diff_item['after'], 'normal-after-value')

    def test_sensitive_container_diff_collapses_at_boundary_for_storage_and_detail(self):
        scenarios = (
            (
                'direct_dict_changed',
                {'headers': {'Authorization': {'credential': 'direct-before'}}},
                {'headers': {'Authorization': {'credential': 'direct-after'}}},
                'headers.Authorization',
                'changed',
                ('direct-before', 'direct-after'),
            ),
            (
                'semantic_dict_changed',
                {'fields': [{'key': 'Authorization', 'value': {'credential': 'semantic-dict-before'}}]},
                {'fields': [{'key': 'Authorization', 'value': {'credential': 'semantic-dict-after'}}]},
                'fields.0.value',
                'changed',
                ('semantic-dict-before', 'semantic-dict-after'),
            ),
            (
                'semantic_list_changed',
                {'fields': [{'name': 'apiKey', 'value': ['semantic-list-before']}]},
                {'fields': [{'name': 'apiKey', 'value': ['semantic-list-after']}]},
                'fields.0.value',
                'changed',
                ('semantic-list-before', 'semantic-list-after'),
            ),
            (
                'direct_inner_child_added',
                {'headers': {'Authorization': {'stable': 'same'}}},
                {'headers': {'Authorization': {'stable': 'same', 'credential': 'inner-added-secret'}}},
                'headers.Authorization',
                'changed',
                ('inner-added-secret',),
            ),
            (
                'semantic_inner_child_removed',
                {
                    'fields': [{
                        'key': 'Authorization',
                        'value': {'stable': 'same', 'credential': 'inner-removed-secret'},
                    }],
                },
                {
                    'fields': [{
                        'key': 'Authorization',
                        'value': {'stable': 'same'},
                    }],
                },
                'fields.0.value',
                'changed',
                ('inner-removed-secret',),
            ),
            (
                'direct_list_added',
                {'headers': {}},
                {'headers': {'api_key': [{'credential': 'added-secret'}]}},
                'headers.api_key',
                'added',
                ('added-secret',),
            ),
            (
                'semantic_dict_removed',
                {'fields': [{'key': 'Authorization', 'value': {'credential': 'removed-secret'}}]},
                {'fields': [{'key': 'Authorization'}]},
                'fields.0.value',
                'removed',
                ('removed-secret',),
            ),
            (
                'dotted_sensitive_list_changed',
                {'api.key': [{'credential': 'dotted-container-before'}]},
                {'api.key': [{'credential': 'dotted-container-after'}]},
                'api.key',
                'changed',
                ('dotted-container-before', 'dotted-container-after'),
            ),
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        for (
                scenario_name,
                before_snapshot,
                after_snapshot,
                expected_path,
                expected_type,
                raw_values,
        ) in scenarios:
            with self.subTest(scenario=scenario_name):
                expected_before = None if expected_type == 'added' else '***'
                expected_after = None if expected_type == 'removed' else '***'
                version = ApiConfigDiffService.record_change(
                    object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
                    object_id=self.api_info.id,
                    action='update',
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                    source='test',
                )
                version.refresh_from_db()
                stored_diff = [item for item in version.diff if item['path'] == expected_path]
                self.assertEqual(len(stored_diff), 1)
                self.assertEqual(stored_diff[0]['type'], expected_type)
                self.assertEqual(stored_diff[0]['before'], expected_before)
                self.assertEqual(stored_diff[0]['after'], expected_after)
                self.assertIs(stored_diff[0].get('masked'), True)
                self.assertFalse(any(
                    item['path'].startswith(f'{expected_path}.')
                    for item in version.diff
                ))
                stored_payload = json.dumps({
                    'before': version.before_snapshot,
                    'after': version.after_snapshot,
                    'diff': version.diff,
                }, ensure_ascii=False)
                for raw_value in raw_values:
                    self.assertNotIn(raw_value, stored_payload)
                self.assertNotIn('_path_segments', stored_payload)
                self.assertNotIn('_sensitive_boundary', stored_payload)

                response = self.client.get(
                    '/api/api/config/version/detail',
                    {'id': version.id},
                    HTTP_AUTHORIZATION=token,
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()['data']
                detail_diff = [item for item in data['diff'] if item['path'] == expected_path]
                self.assertEqual(len(detail_diff), 1)
                self.assertEqual(detail_diff[0]['type'], expected_type)
                self.assertEqual(detail_diff[0]['before'], expected_before)
                self.assertEqual(detail_diff[0]['after'], expected_after)
                serialized_response = json.dumps(data, ensure_ascii=False)
                for raw_value in raw_values:
                    self.assertNotIn(raw_value, serialized_response)
                self.assertNotIn('_path_segments', serialized_response)
                self.assertNotIn('_sensitive_boundary', serialized_response)

    def test_version_detail_collapses_legacy_sensitive_container_diff(self):
        before_snapshot = {'headers': {'Authorization': {'credential': 'legacy-container-before'}}}
        after_snapshot = {'headers': {'Authorization': {'credential': 'legacy-container-after'}}}
        version = ApiConfigVersion.objects.create(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
            version_no=1,
            action='update',
            source='test',
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            diff=[{
                'path': 'headers.Authorization.credential',
                'type': 'changed',
                'before': 'legacy-container-before',
                'after': 'legacy-container-after',
            }],
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(
            '/api/api/config/version/detail',
            {'id': version.id},
            HTTP_AUTHORIZATION=token,
        )

        data = response.json()['data']
        self.assertEqual(data['diff'], [{
            'path': 'headers.Authorization',
            'type': 'changed',
            'before': '***',
            'after': '***',
        }])
        serialized_response = json.dumps(data, ensure_ascii=False)
        self.assertNotIn('legacy-container-before', serialized_response)
        self.assertNotIn('legacy-container-after', serialized_response)

    def test_snapshot_sanitizer_masks_semantic_and_json_secrets_without_losing_large_integers(self):
        value = {
            'fields': [
                {'name': 'apiKey', 'value': 'name-based-value'},
                {'key': 'normal', 'value': {'password': 'nested-value'}},
            ],
            'payload': (
                '{"account_id":9007199254740993,'
                '"credentials":{"X-API-Key":"json-value"},'
                '"fields":[{"key":"Authorization","value":"json-semantic-value"}]}'
            ),
        }

        sanitized = ApiConfigSnapshotService.sanitize_value(value)

        self.assertEqual(sanitized['fields'][0]['value'], '***')
        self.assertEqual(sanitized['fields'][1]['value']['password'], '***')
        self.assertIsInstance(sanitized['payload'], str)
        parsed_payload = json.loads(sanitized['payload'])
        self.assertEqual(parsed_payload['account_id'], 9007199254740993)
        self.assertEqual(parsed_payload['credentials']['X-API-Key'], '***')
        self.assertEqual(parsed_payload['fields'][0]['value'], '***')

    def test_snapshot_sanitizer_preserves_json_with_non_standard_constants(self):
        for value in ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
            with self.subTest(value=value):
                self.assertEqual(ApiConfigSnapshotService.sanitize_value(value), value)

    def test_snapshot_sanitizer_masks_sensitive_malformed_json_hints_only(self):
        sensitive_values = (
            '{"password":"secret",}',
            '{"password":"secret","x":NaN}',
            '{"password":"truncated-secret"',
            '{"key":"Authorization","value":{"credential":"semantic-secret"',
            '{key: Authorization,value:"bare-semantic-secret",}',
            '{"key":/*comment*/"Authorization","value":"comment-semantic-secret","x":NaN}',
            '\ufeff{"password":"bom-secret"}',
            '{"password: "quote-secret"}',
            '{"value":"raw-secret","key":"Authorization',
            '{password/*comment*/:"raw-secret",}',
            '{"value":"raw-secret","key":"Authoriz\\u0061tion',
            "{'p\\u0061ssword':'raw-secret'}",
            "{'value':'raw-secret','key':'Authoriz\\u0061tion'}",
        )
        for value in sensitive_values:
            with self.subTest(value=value):
                self.assertEqual(ApiConfigSnapshotService.sanitize_value(value), '***')

        preserved_values = (
            '{"note":"password and token are ordinary value text",}',
            '{"token_count":1,}',
            '{"passwordless_enabled":true,}',
            '{"x":NaN}',
            '{"note":"password: ordinary value text',
            '["ok","password: ordinary value text",]',
            '["ok","token: ordinary value text",]',
            'password=secret',
        )
        for value in preserved_values:
            with self.subTest(value=value):
                self.assertEqual(ApiConfigSnapshotService.sanitize_value(value), value)

    def test_escaped_sensitive_selector_does_not_leak_storage_or_detail(self):
        before_secret = 'escaped-selector-before-secret'
        after_secret = 'escaped-selector-after-secret'
        version = ApiConfigDiffService.record_change(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
            action='update',
            before_snapshot={
                'payload': f'{{"value":"{before_secret}","key":"Authoriz\\u0061tion',
            },
            after_snapshot={
                'payload': f'{{"value":"{after_secret}","key":"Authoriz\\u0061tion',
            },
            source='test',
        )
        version.refresh_from_db()
        stored_audit = json.dumps({
            'before': version.before_snapshot,
            'after': version.after_snapshot,
            'diff': version.diff,
        }, ensure_ascii=False)
        self.assertNotIn(before_secret, stored_audit)
        self.assertNotIn(after_secret, stored_audit)

        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')
        response = self.client.get(
            '/api/api/config/version/detail',
            {'id': version.id},
            HTTP_AUTHORIZATION=token,
        )
        self.assertEqual(response.status_code, 200)
        serialized_response = json.dumps(response.json()['data'], ensure_ascii=False)
        self.assertNotIn(before_secret, serialized_response)
        self.assertNotIn(after_secret, serialized_response)

    def test_pair_sensitive_transitions_mask_storage_diff_and_detail(self):
        scenarios = (
            (
                'semantic_becomes_sensitive',
                {'fields': [{'key': 'normal', 'value': 'transition-to-sensitive-secret'}]},
                {'fields': [{'key': 'Authorization', 'value': 'transition-to-sensitive-secret'}]},
                ('transition-to-sensitive-secret',),
            ),
            (
                'semantic_becomes_normal',
                {'fields': [{'key': 'Authorization', 'value': 'transition-from-sensitive-secret'}]},
                {'fields': [{'key': 'normal', 'value': 'transition-from-sensitive-secret'}]},
                ('transition-from-sensitive-secret',),
            ),
            (
                'valid_json',
                {'payload': '{"key":"normal","value":"valid-json-transition-secret"}'},
                {'payload': '{"key":"Authorization","value":"valid-json-transition-secret"}'},
                ('valid-json-transition-secret',),
            ),
            (
                'malformed_json',
                {'payload': '{key: normal,value:"malformed-json-transition-secret",}'},
                {'payload': '{key: Authorization,value:"malformed-json-transition-secret",}'},
                ('malformed-json-transition-secret',),
            ),
            (
                'semantic_object_to_scalar',
                {'field': {'key': 'Authorization', 'value': 'object-side-secret'}},
                {'field': 'scalar-side-secret'},
                ('object-side-secret', 'scalar-side-secret'),
            ),
            (
                'scalar_to_semantic_object',
                {'field': 'before-scalar-secret'},
                {'field': {'name': 'apiKey', 'value': 'after-object-secret'}},
                ('before-scalar-secret', 'after-object-secret'),
            ),
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        for scenario_name, before_snapshot, after_snapshot, secrets in scenarios:
            with self.subTest(scenario=scenario_name):
                version = ApiConfigDiffService.record_change(
                    object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
                    object_id=self.api_info.id,
                    action='update',
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                    source='test',
                )
                version.refresh_from_db()
                stored_audit = json.dumps({
                    'before': version.before_snapshot,
                    'after': version.after_snapshot,
                    'diff': version.diff,
                }, ensure_ascii=False)
                self.assertIn('***', stored_audit)
                for secret in secrets:
                    self.assertNotIn(secret, stored_audit)

                response = self.client.get(
                    '/api/api/config/version/detail',
                    {'id': version.id},
                    HTTP_AUTHORIZATION=token,
                )
                self.assertEqual(response.status_code, 200)
                serialized_response = json.dumps(response.json()['data'], ensure_ascii=False)
                for secret in secrets:
                    self.assertNotIn(secret, serialized_response)

    def test_literal_mask_is_not_redaction_provenance(self):
        safe_before, safe_after, safe_diff = ApiConfigDiffService.sanitize_audit_data(
            {'normal': '***'},
            {'normal': 'visible'},
        )
        self.assertEqual(safe_before, {'normal': '***'})
        self.assertEqual(safe_after, {'normal': 'visible'})
        self.assertEqual(safe_diff, [{
            'path': 'normal',
            'type': 'changed',
            'before': '***',
            'after': 'visible',
        }])

        _, _, candidate_diff = ApiConfigDiffService.sanitize_audit_data(
            {'normal': '***'},
            {'normal': '***'},
            candidate_diff=[{
                'path': 'normal',
                'type': 'changed',
                'before': 'candidate-before',
                'after': 'candidate-after',
            }],
        )
        self.assertEqual(candidate_diff, [])

    def test_masked_diff_sidecar_proves_folded_paths_without_leaking(self):
        scenarios = (
            (
                'malformed',
                {'payload': '{"password":"marker-malformed-before",}'},
                {'payload': '{"password":"marker-malformed-after",}'},
                'payload',
                ('marker-malformed-before', 'marker-malformed-after'),
            ),
            (
                'type_transition',
                {'field': {'key': 'Authorization', 'value': 'marker-object-secret'}},
                {'field': 'marker-scalar-secret'},
                'field',
                ('marker-object-secret', 'marker-scalar-secret'),
            ),
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        for scenario_name, before_snapshot, after_snapshot, expected_path, secrets in scenarios:
            with self.subTest(scenario=scenario_name):
                version = ApiConfigDiffService.record_change(
                    object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
                    object_id=self.api_info.id,
                    action='update',
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                    source='test',
                )
                version.refresh_from_db()
                self.assertEqual(version.before_snapshot[expected_path], '***')
                self.assertEqual(version.after_snapshot[expected_path], '***')
                stored_item = next(item for item in version.diff if item['path'] == expected_path)
                self.assertIs(stored_item.get('masked'), True)
                self.assertEqual(stored_item['before'], '***')
                self.assertEqual(stored_item['after'], '***')
                stored_audit = json.dumps({
                    'before': version.before_snapshot,
                    'after': version.after_snapshot,
                    'diff': version.diff,
                }, ensure_ascii=False)
                for secret in secrets:
                    self.assertNotIn(secret, stored_audit)

                response = self.client.get(
                    '/api/api/config/version/detail',
                    {'id': version.id},
                    HTTP_AUTHORIZATION=token,
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()['data']
                self.assertEqual(data['before_snapshot'][expected_path], '***')
                self.assertEqual(data['after_snapshot'][expected_path], '***')
                self.assertIn(expected_path, {item['path'] for item in data['diff']})
                serialized_response = json.dumps(data, ensure_ascii=False)
                self.assertNotIn('"masked"', serialized_response)
                for secret in secrets:
                    self.assertNotIn(secret, serialized_response)

                version.refresh_from_db()
                self.assertEqual(version.before_snapshot[expected_path], '***')
                self.assertEqual(version.after_snapshot[expected_path], '***')
                self.assertIs(
                    next(item for item in version.diff if item['path'] == expected_path).get('masked'),
                    True,
                )

    def test_old_marker_shape_is_ordinary_and_cannot_prove_candidate(self):
        old_marker_shape = {'__mango_api_config_audit__': 'redacted:v1'}
        before_snapshot = {'normal': old_marker_shape}
        after_snapshot = {'normal': {'visible': 'ordinary'}}

        safe_before, safe_after, _ = ApiConfigDiffService.sanitize_audit_data(
            before_snapshot,
            after_snapshot,
        )
        self.assertEqual(safe_before, before_snapshot)
        self.assertEqual(safe_after, after_snapshot)

        _, _, candidate_diff = ApiConfigDiffService.sanitize_audit_data(
            before_snapshot,
            before_snapshot,
            candidate_diff=[{
                'path': 'normal',
                'type': 'changed',
                'before': 'forged-before',
                'after': 'forged-after',
            }],
        )
        self.assertEqual(candidate_diff, [])

    def test_sensitive_key_matching_is_normalized_and_does_not_use_substrings(self):
        self.assertTrue(ApiConfigSnapshotService.is_sensitive_key('X-API-Key'))
        self.assertTrue(ApiConfigSnapshotService.is_sensitive_key('apiKey'))
        self.assertTrue(ApiConfigSnapshotService.is_sensitive_key('client_token'))
        self.assertTrue(ApiConfigSnapshotService.is_sensitive_key('access_token'))
        self.assertTrue(ApiConfigSnapshotService.is_sensitive_key('refreshToken'))
        self.assertTrue(ApiConfigSnapshotService.is_sensitive_key('Proxy-Authorization'))
        self.assertFalse(ApiConfigSnapshotService.is_sensitive_key('page_token'))
        self.assertFalse(ApiConfigSnapshotService.is_sensitive_key('pageToken'))
        self.assertFalse(ApiConfigSnapshotService.is_sensitive_key('next_page_token'))
        self.assertFalse(ApiConfigSnapshotService.is_sensitive_key('token_count'))
        self.assertFalse(ApiConfigSnapshotService.is_sensitive_key('passwordless_enabled'))
        sanitized = ApiConfigSnapshotService.sanitize_value({
            'page_token': 'opaque-page-cursor',
            'nextPageToken': 'opaque-next-page-cursor',
            'access_token': 'plaintext-auth-token',
            'Proxy-Authorization': {'credential': 'direct-proxy-secret'},
            'fields': [
                {'key': 'page_token', 'value': 'semantic-page-cursor'},
                {'key': 'Proxy-Authorization', 'value': 'semantic-proxy-secret'},
            ],
        })
        self.assertEqual(sanitized['page_token'], 'opaque-page-cursor')
        self.assertEqual(sanitized['nextPageToken'], 'opaque-next-page-cursor')
        self.assertEqual(sanitized['access_token'], '***')
        self.assertEqual(sanitized['Proxy-Authorization'], '***')
        self.assertEqual(sanitized['fields'][0]['value'], 'semantic-page-cursor')
        self.assertEqual(sanitized['fields'][1]['value'], '***')

    def test_case_snapshot_contains_steps_and_scenarios_without_runtime_result(self):
        snapshot = ApiConfigSnapshotService.capture_api_case(self.case.id)

        self.assertEqual(snapshot['id'], self.case.id)
        self.assertEqual(snapshot['steps'][0]['id'], self.step.id)
        self.assertEqual(snapshot['steps'][0]['parameters'][0]['name'], '创建订单成功')
        self.assertNotIn('result_data', snapshot['steps'][0]['parameters'][0])

    def test_scenario_change_records_parent_case_version(self):
        before_snapshot = ApiConfigSnapshotService.capture_for_instance(self.parameter).snapshot
        self.parameter.name = '创建订单异常'
        self.parameter.save()

        version = ApiConfigDiffService.record_instance_change(
            self.parameter,
            action='update_scenario',
            before_snapshot=before_snapshot,
            source='test',
        )

        self.assertEqual(version.object_type, ApiConfigVersion.OBJECT_TYPE_API_CASE)
        self.assertEqual(version.object_id, self.case.id)
        self.assertIn('steps.0.parameters.0.name', {item['path'] for item in version.diff})

    def test_inside_put_records_api_info_version(self):
        from src.apps.auto_api.api.views.api_info import ApiInfoCRUD

        ApiInfoCRUD.inside_put(self.api_info.id, {'id': self.api_info.id, 'name': 'inside修改'})

        version = ApiConfigVersion.objects.get(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
        )
        self.assertEqual(version.action, 'update')
        self.assertIn('name', {item['path'] for item in version.diff})

    def test_version_history_api_returns_list_and_detail(self):
        version = ApiConfigDiffService.record_instance_change(
            self.api_info,
            action='update',
            before_snapshot=None,
            source='test',
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(
            '/api/api/config/version',
            {'object_type': ApiConfigVersion.OBJECT_TYPE_API_INFO, 'object_id': self.api_info.id},
            HTTP_AUTHORIZATION=token,
        )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body['code'], 200)
        self.assertEqual(body['data'][0]['id'], version.id)

        detail_response = self.client.get(
            '/api/api/config/version/detail',
            {'id': version.id},
            HTTP_AUTHORIZATION=token,
        )
        detail_body = detail_response.json()
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_body['code'], 200)
        self.assertEqual(detail_body['data']['id'], version.id)

    def test_version_detail_preserves_only_proven_redacted_candidate_paths(self):
        scenarios = (
            (
                'semantic',
                {'body_config': {'fields': [{'key': 'Authorization', 'value': 'semantic-before'}]}},
                {'body_config': {'fields': [{'key': 'Authorization', 'value': 'semantic-after'}]}},
                'body_config.fields.0.value',
                ('semantic-before', 'semantic-after'),
            ),
            (
                'direct',
                {'headers': {'Authorization': 'direct-before'}},
                {'headers': {'Authorization': 'direct-after'}},
                'headers.Authorization',
                ('direct-before', 'direct-after'),
            ),
            (
                'json_string',
                {'payload': '{"password":"json-before"}'},
                {'payload': '{"password":"json-after"}'},
                'payload',
                ('json-before', 'json-after'),
            ),
            (
                'malformed_json_string',
                {'payload': '{"password":"malformed-before",}'},
                {'payload': '{"password":"malformed-after",}'},
                'payload',
                ('malformed-before', 'malformed-after'),
            ),
            (
                'dotted_key',
                {'payload.with.dot': [{'name': 'apiKey', 'value': 'dotted-before'}]},
                {'payload.with.dot': [{'name': 'apiKey', 'value': 'dotted-after'}]},
                'payload.with.dot.0.value',
                ('dotted-before', 'dotted-after'),
            ),
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        for scenario_name, before_snapshot, after_snapshot, expected_path, raw_values in scenarios:
            with self.subTest(scenario=scenario_name):
                version = ApiConfigDiffService.record_change(
                    object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
                    object_id=self.api_info.id,
                    action='update',
                    before_snapshot=before_snapshot,
                    after_snapshot=after_snapshot,
                    source='test',
                )
                self.assertIn(expected_path, {item['path'] for item in version.diff})
                self.assertIs(
                    next(item for item in version.diff if item['path'] == expected_path).get('masked'),
                    True,
                )
                unsafe_before = f'stored-unsafe-before-{scenario_name}'
                unsafe_after = f'stored-unsafe-after-{scenario_name}'
                version.diff = [
                    {
                        **item,
                        'before': unsafe_before,
                        'after': unsafe_after,
                    }
                    if item['path'] == expected_path else item
                    for item in version.diff
                ]
                unproven_path = f'{expected_path}.unproven'
                version.diff.append({
                    'path': unproven_path,
                    'type': 'changed',
                    'before': unsafe_before,
                    'after': unsafe_after,
                })
                version.save(update_fields=['diff'])

                response = self.client.get(
                    '/api/api/config/version/detail',
                    {'id': version.id},
                    HTTP_AUTHORIZATION=token,
                )

                self.assertEqual(response.status_code, 200)
                data = response.json()['data']
                diff_by_path = {item['path']: item for item in data['diff']}
                self.assertIn(expected_path, diff_by_path)
                self.assertNotIn(unproven_path, diff_by_path)
                self.assertEqual(diff_by_path[expected_path]['before'], '***')
                self.assertEqual(diff_by_path[expected_path]['after'], '***')
                self.assertIn(expected_path, data['changed_fields'])
                serialized_response = json.dumps(data, ensure_ascii=False)
                self.assertNotIn(unsafe_before, serialized_response)
                self.assertNotIn(unsafe_after, serialized_response)
                for raw_value in raw_values:
                    self.assertNotIn(raw_value, serialized_response)

    def test_version_detail_rejects_sensitive_ancestors_and_ambiguous_display_path(self):
        before_snapshot = {
            'body_config': {
                'fields': [{'key': 'Authorization', 'value': 'semantic-before'}],
            },
            'api.key': 'dotted-before',
            'api': {'key': 'ordinary-value'},
        }
        after_snapshot = {
            'body_config': {
                'fields': [{'key': 'Authorization', 'value': 'semantic-after'}],
            },
            'api.key': 'dotted-after',
            'api': {'key': 'ordinary-value'},
        }
        version = ApiConfigDiffService.record_change(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
            action='update',
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            source='test',
        )
        unsafe_value = 'stored-candidate-must-not-be-used'
        legitimate_path = 'body_config.fields.0.value'
        rejected_paths = (
            '$',
            'body_config',
            'body_config.fields',
            'body_config.fields.0',
            'body_config.fields.0.value.unproven',
            'api.key',
        )
        version.diff = [
            {
                'path': legitimate_path,
                'type': 'added',
                'before': unsafe_value,
                'after': unsafe_value,
                'masked': True,
            },
            *[
                {
                    'path': path,
                    'type': 'changed',
                    'before': unsafe_value,
                    'after': unsafe_value,
                    **(
                        {'masked': True}
                        if path in ('body_config.fields.0.value.unproven', 'api.key')
                        else {}
                    ),
                }
                for path in rejected_paths
            ],
        ]
        version.save(update_fields=['diff'])
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(
            '/api/api/config/version/detail',
            {'id': version.id},
            HTTP_AUTHORIZATION=token,
        )

        data = response.json()['data']
        diff_by_path = {item['path']: item for item in data['diff']}
        self.assertEqual(set(diff_by_path), {legitimate_path})
        self.assertEqual(diff_by_path[legitimate_path]['type'], 'changed')
        self.assertEqual(diff_by_path[legitimate_path]['before'], '***')
        self.assertEqual(diff_by_path[legitimate_path]['after'], '***')
        self.assertNotIn(unsafe_value, json.dumps(data, ensure_ascii=False))

    def test_version_detail_masks_legacy_snapshots_and_rebuilds_unsafe_diff_without_database_writeback(self):
        before_snapshot = {
            'project_product': self.product.id,
            'module': self.module.id,
            'body_config': {
                'fields': [
                    {'key': 'Authorization', 'value': 'legacy-before-authorization'},
                    {'name': 'apiKey', 'value': 'legacy-before-api-key'},
                ],
            },
            'payload.with.dot': [
                {'key': 'Authorization', 'value': 'legacy-dotted-before'},
            ],
        }
        after_snapshot = {
            'project_product': self.product.id,
            'module': self.module.id,
            'body_config': {
                'fields': [
                    {'key': 'Authorization', 'value': 'legacy-after-authorization'},
                    {'name': 'apiKey', 'value': 'legacy-after-api-key'},
                ],
            },
            'payload.with.dot': [
                {'key': 'Authorization', 'value': 'legacy-dotted-after'},
            ],
        }
        unsafe_diff = [
            {
                'path': 'unsafe.stored.path',
                'type': 'changed',
                'before': 'unsafe-stored-before',
                'after': 'unsafe-stored-after',
            },
            {
                'path': 'body_config.fields.0.value.unproven',
                'type': 'changed',
                'before': 'unsafe-unproven-before',
                'after': 'unsafe-unproven-after',
            },
        ]
        version = ApiConfigVersion.objects.create(
            object_type=ApiConfigVersion.OBJECT_TYPE_API_INFO,
            object_id=self.api_info.id,
            version_no=1,
            project_product=self.product,
            module=self.module,
            action='update',
            source='test',
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            diff=unsafe_diff,
        )
        token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

        response = self.client.get(
            '/api/api/config/version/detail',
            {'id': version.id},
            HTTP_AUTHORIZATION=token,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['code'], 200)
        data = body['data']
        for snapshot_name in ('before_snapshot', 'after_snapshot'):
            self.assertEqual(data[snapshot_name]['body_config']['fields'][0]['value'], '***')
            self.assertEqual(data[snapshot_name]['body_config']['fields'][1]['value'], '***')
        diff_by_path = {item['path']: item for item in data['diff']}
        self.assertEqual(data['changed_fields'], [item['path'] for item in data['diff']])
        for path in ('body_config.fields.0.value', 'body_config.fields.1.value'):
            self.assertEqual(diff_by_path[path]['before'], '***')
            self.assertEqual(diff_by_path[path]['after'], '***')
        self.assertEqual(diff_by_path['payload.with.dot.0.value']['before'], '***')
        self.assertEqual(diff_by_path['payload.with.dot.0.value']['after'], '***')
        serialized_response = json.dumps(data, ensure_ascii=False)
        for unsafe_value in (
                'legacy-before-authorization',
                'legacy-after-authorization',
                'legacy-before-api-key',
                'legacy-after-api-key',
                'unsafe-stored-before',
                'unsafe-stored-after',
                'legacy-dotted-before',
                'legacy-dotted-after',
        ):
            self.assertNotIn(unsafe_value, serialized_response)

        version.refresh_from_db()
        self.assertEqual(
            version.before_snapshot['body_config']['fields'][0]['value'],
            'legacy-before-authorization',
        )
        self.assertEqual(version.diff, unsafe_diff)

        list_response = self.client.get(
            '/api/api/config/version',
            {'object_type': ApiConfigVersion.OBJECT_TYPE_API_INFO, 'object_id': self.api_info.id},
            HTTP_AUTHORIZATION=token,
        )
        list_item = next(item for item in list_response.json()['data'] if item['id'] == version.id)
        self.assertEqual(set(list_item['changed_fields']), set(diff_by_path))
        self.assertNotIn('unsafe.stored.path', list_item['changed_fields'])
        self.assertNotIn('body_config.fields.0.value.unproven', list_item['changed_fields'])


class CaseBaseParametrizeTests(SimpleTestCase):
    class FakeTestData:

        def __init__(self):
            self.cache = {}

        def replace(self, value):
            return value

        def set_cache(self, key, value):
            self.cache[key] = value

        def get_cache(self, key):
            return self.cache.get(key)

        def set_data_factory_cache(self, key, value):
            self.cache[key] = value

    def make_case_base(self):
        test_data = self.FakeTestData()
        test_setup = SimpleNamespace(test_data=test_data)
        return CaseBase(test_setup, SimpleNamespace(), test_env=0), test_data

    def test_case_parametrize_allows_empty_values(self):
        case_base, test_data = self.make_case_base()

        case_base.case_parametrize({
            'parametrize': [
                {'key': 'empty_text', 'value': ''},
                {'key': 'null_value', 'value': None},
                {'key': 'missing_value'},
                {'key': 'zero_value', 'value': 0},
                {'key': 'false_value', 'value': False},
                {'key': 'empty_list', 'value': []},
            ]
        })

        self.assertEqual(test_data.cache, {
            'empty_text': '',
            'null_value': None,
            'missing_value': None,
            'zero_value': 0,
            'false_value': False,
            'empty_list': [],
        })

    def test_case_parametrize_skips_unmatched_environment_and_allows_override(self):
        case_base, test_data = self.make_case_base()

        case_base.case_parametrize({
            'parametrize': [
                {'key': 'missing_env', 'value': 'common'},
                {'key': 'null_env', 'value': 'common', 'test_envs': None},
                {'key': 'empty_env', 'value': 'common', 'test_envs': []},
                {'key': 'tenant', 'value': 'test-env', 'test_envs': [0]},
                {'key': 'tenant', 'value': 'dev-env', 'test_envs': [3]},
                {'key': 'only_dev', 'value': 'skip', 'test_envs': [3]},
            ]
        })

        self.assertEqual(test_data.cache, {
            'missing_env': 'common',
            'null_env': 'common',
            'empty_env': 'common',
            'tenant': 'test-env',
        })

    def test_front_custom_skips_unmatched_environment_and_allows_override(self):
        case_base, test_data = self.make_case_base()

        case_base._CaseBase__front_custom([
            {'key': 'missing_env', 'value': 'common'},
            {'key': 'null_env', 'value': 'common', 'test_envs': None},
            {'key': 'empty_env', 'value': 'common', 'test_envs': []},
            {'key': 'token', 'value': 'test-token', 'test_envs': [0]},
            {'key': 'token', 'value': 'dev-token', 'test_envs': [3]},
            {'key': 'only_dev', 'value': 'skip', 'test_envs': [3]},
        ])

        self.assertEqual(test_data.cache, {
            'missing_env': 'common',
            'null_env': 'common',
            'empty_env': 'common',
            'token': 'test-token',
        })

    def test_case_parametrize_still_rejects_empty_key(self):
        case_base, _ = self.make_case_base()

        with self.assertRaises(AutoApiError):
            case_base.case_parametrize({'parametrize': [{'key': '', 'value': 'ok'}]})

    def test_parametrize_schema_allows_null_and_missing_values(self):
        parametrize = ApiParametrizeSuite.model_validate({
            'name': '参数组1',
            'parametrize': [
                {'key': 'null_value', 'value': None},
                {'key': 'missing_value'},
            ]
        })

        self.assertEqual(parametrize.model_dump(), {
            'name': '参数组1',
            'parametrize': [
                {'key': 'null_value', 'value': None, 'test_envs': []},
                {'key': 'missing_value', 'value': None, 'test_envs': []},
            ],
        })


class ApiSqlExecutionEnvironmentTests(SimpleTestCase):
    class FakeTestData:

        @staticmethod
        def replace(value):
            return value

    @staticmethod
    def fail_get_db_connection(*_args, **_kwargs):
        raise AssertionError('环境不匹配时不应获取数据库连接')

    def test_sql_schema_defaults_missing_and_null_environments_to_all(self):
        rows = validate_sql_item_list([
            {'key': 'first', 'value': 'SELECT 1', 'datasource_alias': 1},
            {'key': 'second', 'value': 'SELECT 2', 'datasource_alias': 1, 'test_envs': None},
        ], '前置SQL')

        self.assertEqual(rows[0]['test_envs'], [])
        self.assertEqual(rows[1]['test_envs'], [])

    def test_sql_schema_normalizes_duplicate_environments(self):
        rows = validate_sql_item_list([
            {
                'key': 'user',
                'value': 'SELECT id FROM user',
                'datasource_alias': 1,
                'test_envs': [0, 3, 0],
            },
        ], '前置SQL')

        self.assertEqual(rows[0]['test_envs'], [0, 3])

    def test_sql_schema_rejects_invalid_environment(self):
        with self.assertRaises(AutoApiError):
            validate_sql_item_list([
                {'key': '', 'value': 'DELETE FROM user', 'datasource_alias': 1, 'test_envs': [99]},
            ], '后置SQL')

    def test_environment_match_rule(self):
        self.assertTrue(should_execute_sql({}, 2))
        self.assertTrue(should_execute_sql({'test_envs': None}, 2))
        self.assertTrue(should_execute_sql({'test_envs': []}, 2))
        self.assertTrue(should_execute_sql({'test_envs': [0, 3]}, 3))
        self.assertFalse(should_execute_sql({'test_envs': [0, 3]}, 2))

    def test_case_and_scenario_sql_skip_before_database_connection(self):
        test_setup = SimpleNamespace(
            test_data=self.FakeTestData(),
            test_object=None,
            get_db_connection=self.fail_get_db_connection,
        )
        sql_rows = [
            {'key': '', 'value': 'DELETE FROM user', 'datasource_alias': 1, 'test_envs': [0, 3]},
        ]
        case_base = CaseBase(test_setup, SimpleNamespace(), test_env=2)
        case_parameter = CaseParameter(test_setup, SimpleNamespace(), SimpleNamespace(), test_env=2)

        case_base._CaseBase__front_sql(sql_rows)
        case_base._CaseBase__posterior_sql(sql_rows)
        case_parameter._CaseParameter__front_sql(sql_rows)
        case_parameter._CaseParameter__posterior_sql(sql_rows)


class ApiResponseJsonScalarTests(SimpleTestCase):
    class FakeTestData:

        def replace(self, value):
            return value

        def get_json_path_value(self, response, expression):
            return response[expression]

    def make_case_parameter(self):
        test_setup = SimpleNamespace(test_data=self.FakeTestData(), test_object=None)
        parameter = SimpleNamespace()
        api_info = SimpleNamespace(is_schema=0, ass_schema=None)
        return CaseParameter(test_setup, parameter, api_info, test_env=0)

    def test_response_model_accepts_json_scalar_values(self):
        for value in [True, False, 'ok', 1, 1.5, None, {'ok': True}, [1]]:
            response = ApiExecutionResponse(
                code=200,
                time=0.1,
                headers={},
                json=value,
                text='true' if value is True else str(value),
            )

            self.assertEqual(response.json, value)

    def test_request_model_allows_json_scalar_body(self):
        request = ApiExecutionRequest(
            method='POST',
            url='https://example.test',
            body_type='json',
            body_config={'source_type': 'template', 'body_text': 'true'},
        )

        request.serialize()

        self.assertEqual(request.body_type, 'json')
        self.assertEqual(request.body_config['body_text'], 'true')

    def test_posterior_jsonpath_miss_includes_operation_key_and_failed_index(self):
        with self.assertRaises(AutoApiError) as context:
            extract_jsonpath_value(
                {'data': {'contract_texts': []}},
                '$.data.contract_texts.0.file_id',
                operation='用例场景后置JSONPath提取',
                cache_key='contract_file_id',
            )

        self.assertIn('用例场景后置JSONPath提取失败', context.exception.msg)
        self.assertIn('目标缓存Key：【contract_file_id】', context.exception.msg)
        self.assertIn('空数组', context.exception.msg)
        self.assertIn('下标【0】', context.exception.msg)

    def test_jsonpath_assertion_rejects_scalar_response_with_business_error(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(ApiExecutionResponse(
                code=200, time=0.1, headers={}, json=True, text='true'
            ), [
                {'actual': '$.success', 'method': 'p_is_true', 'expect': None}
            ])

        self.assertIn('不支持JSONPath处理', context.exception.msg)

    def test_text_assertion_supports_boolean_response_text(self):
        case_parameter = self.make_case_parameter()

        case_parameter._CaseParameter__ass_test_all('true', 'true')

        self.assertEqual(case_parameter.ass_result[0].status, 1)

    def test_jsonpath_assertion_or_group_passes_when_any_item_passes(self):
        case_parameter = self.make_case_parameter()

        case_parameter._CaseParameter__ass_jsonpath(ApiExecutionResponse(
            code=200, time=0.1, headers={}, json={'code': 201}, text='{"code":201}'
        ), [
            {
                'group_name': '状态码兼容',
                'group_logic': 'OR',
                'actual': '$.code',
                'method': 'p_is_equal_to',
                'expect': 200,
            },
            {
                'group_name': '状态码兼容',
                'group_logic': 'OR',
                'actual': '$.code',
                'method': 'p_is_equal_to',
                'expect': 201,
            },
        ])

        self.assertEqual(case_parameter.ass_result[-1].status, 1)
        self.assertEqual(case_parameter.ass_result[-1].group_logic, 'OR')

    def test_jsonpath_assertion_without_group_logic_keeps_and_behavior(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(AutoApiError):
            case_parameter._CaseParameter__ass_jsonpath(ApiExecutionResponse(
                code=200, time=0.1, headers={}, json={'code': 201}, text='{"code":201}'
            ), [
                {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200},
                {'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 201},
            ])


class RequestModelParamsTests(SimpleTestCase):

    def test_params_allows_query_string(self):
        request = ApiExecutionRequest(method='GET', url='https://example.test', params='case_id=21')

        request.serialize()

        self.assertEqual(request.params, 'case_id=21')

    def test_params_keeps_json_scalar_as_query_string(self):
        request = ApiExecutionRequest(method='GET', url='https://example.test', params='21')

        request.serialize()

        self.assertEqual(request.params, '21')

    def test_params_still_parses_json_object_and_array(self):
        request = ApiExecutionRequest(method='GET', url='https://example.test', params='{"case_id": 21}')
        request.serialize()
        self.assertEqual(request.params, {'case_id': 21})

        request = ApiExecutionRequest(method='GET', url='https://example.test', params='[["case_id", 21]]')
        request.serialize()
        self.assertEqual(request.params, [['case_id', 21]])

    def test_params_rejects_malformed_json_object(self):
        request = ApiExecutionRequest(method='GET', url='https://example.test', params='{"case_id":')

        with self.assertRaises(AutoApiError):
            request.serialize()


class HttpPathParamsTests(SimpleTestCase):

    def test_path_params_are_substituted_and_removed_from_query(self):
        from src.apps.auto_api.services.protocols.utils import resolve_http_path_params

        url, params = resolve_http_path_params(
            'https://example.test/contracts/{contractId}/fields/{fieldKey}',
            {'contractId': 123, 'fieldKey': '订单 名称', 'timeRange': 30},
        )

        self.assertEqual(url, 'https://example.test/contracts/123/fields/%E5%90%88%E5%90%8C%20%E5%90%8D%E7%A7%B0')
        self.assertEqual(params, {'timeRange': 30})

    def test_missing_path_param_is_left_for_server_validation(self):
        from src.apps.auto_api.services.protocols.utils import resolve_http_path_params

        url, params = resolve_http_path_params(
            'https://example.test/contracts/{contractId}',
            {'timeRange': 30},
        )

        self.assertEqual(url, 'https://example.test/contracts/{contractId}')
        self.assertEqual(params, {'timeRange': 30})


class RequestBodyRawTests(SimpleTestCase):

    def test_raw_body_defaults_to_application_json(self):
        request = ApiExecutionRequest(
            method='POST',
            url='https://example.test',
            body_type='raw',
            body_config={'body_text': '{"ok": true}'},
        )

        prepared_body = prepare_request_body(request, None)

        self.assertEqual(prepared_body.content_type, 'application/json')
        self.assertEqual(prepared_body.kwargs, {'content': '{"ok": true}'})

    def test_content_type_header_is_added_when_missing(self):
        headers = BaseRequest._headers_with_content_type({'Accept': 'application/json'}, 'application/json')

        self.assertEqual(headers, {'Accept': 'application/json', 'Content-Type': 'application/json'})

    def test_content_type_header_keeps_user_value(self):
        headers = BaseRequest._headers_with_content_type({'content-type': 'application/xml'}, 'application/json')

        self.assertEqual(headers, {'content-type': 'application/xml'})

    def test_multipart_content_type_header_is_removed(self):
        headers = BaseRequest._headers_with_content_type(
            {'Accept': 'application/json', 'Content-Type': 'multipart/form-data'},
            'multipart/form-data',
        )

        self.assertEqual(headers, {'Accept': 'application/json'})

    def test_api_info_serializer_defaults_raw_content_type(self):
        serializer = ApiInfoSerializers()

        attrs = serializer.validate({'body_type': 'raw', 'body_config': {'body_text': 'hello'}})

        self.assertEqual(attrs['body_config']['content_type'], 'application/json')

    def test_api_info_serializer_drops_legacy_body_fields(self):
        serializer = ApiInfoSerializers()

        attrs = serializer.validate({'data': '{"a": 1}', 'json': '{"b": 2}', 'file': [], 'is_text_data': 1})

        self.assertNotIn('data', attrs)
        self.assertNotIn('json', attrs)
        self.assertNotIn('file', attrs)
        self.assertNotIn('is_text_data', attrs)


class ApiPosteriorRegexTests(SimpleTestCase):
    class FakeTestData:

        def replace(self, value):
            return value

    def test_invalid_regex_raises_business_error(self):
        test_setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        test_setup.test_data = self.FakeTestData()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, text='hello')

        with self.assertRaises(AutoApiError) as context:
            test_setup.api_info_posterior_json_re(
                [{'key': 'token', 'value': '(?<=a+)b'}],
                response,
            )

        self.assertIn('API信息后置正则提取失败', context.exception.msg)
        self.assertIn('缓存Key：【token】', context.exception.msg)

    def test_unmatched_regex_reports_key_expression_and_response_length(self):
        test_setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        test_setup.test_data = self.FakeTestData()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, text='hello')

        with self.assertRaises(AutoApiError) as context:
            test_setup.api_info_posterior_json_re(
                [{'key': 'token', 'value': 'token=(\\w+)'}],
                response,
            )

        self.assertIn('后置正则提取未匹配到内容', context.exception.msg)
        self.assertIn('缓存Key：【token】', context.exception.msg)
        self.assertIn('表达式：【token=(\\w+)】', context.exception.msg)
        self.assertIn('响应文本长度：【5】', context.exception.msg)

    def test_posterior_function_syntax_error_reports_line(self):
        test_setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        test_setup.test_data = self.FakeTestData()

        with self.assertRaises(AutoApiError) as context:
            test_setup.execute_analytic_func(
                'def func(self, response)\n    return response',
                None,
                None,
                error_msg=API_POST_FUNCTION_FAILED,
            )

        self.assertIn('接口后置自定义函数执行失败', context.exception.msg)
        self.assertIn('第1行语法错误', context.exception.msg)

    def test_posterior_function_runtime_error_keeps_exception_type_and_reason(self):
        test_setup = APIBaseTestSetup.__new__(APIBaseTestSetup)
        test_setup.test_data = self.FakeTestData()

        with self.assertRaises(AutoApiError) as context:
            test_setup.execute_analytic_func(
                "def func(self, response):\n    raise AssertionError('update_time is empty')",
                None,
                None,
                error_msg=API_POST_FUNCTION_FAILED,
            )

        self.assertIn('接口后置自定义函数执行失败', context.exception.msg)
        self.assertIn('AssertionError: update_time is empty', context.exception.msg)

    def test_api_case_parameter_serializer_defaults_raw_content_type(self):
        serializer = ApiCaseDetailedParameterSerializers()

        attrs = serializer.validate({'body_type': 'raw', 'body_config': {'body_text': 'hello'}})

        self.assertEqual(attrs['body_config']['content_type'], 'application/json')

    def test_api_case_parameter_serializer_drops_legacy_body_fields(self):
        serializer = ApiCaseDetailedParameterSerializers()

        attrs = serializer.validate({'data': '{"a": 1}', 'json': '{"b": 2}', 'file': []})

        self.assertNotIn('data', attrs)
        self.assertNotIn('json', attrs)
        self.assertNotIn('file', attrs)


class ApiAssertionVerificationServiceTests(SimpleTestCase):
    class FakeTestData:

        def __init__(self):
            self.cache = {}

        def replace(self, value):
            return value

        def set_cache(self, key, value):
            self.cache[key] = value

        def get_cache(self, key):
            return self.cache.get(key)

    def setUp(self):
        api_info = SimpleNamespace(
            is_schema=StatusEnum.FAIL.value,
            ass_schema=None,
        )
        self.parameter = SimpleNamespace(
            id=1001,
            case_detailed=SimpleNamespace(api_info=api_info),
            name='断言验证场景',
            ass_json_all=None,
            ass_text_all=None,
            ass_jsonpath=[],
            ass_schema=None,
            ass_general=[],
            result_data={
                'test_time': '2026-07-13 23:30:00',
                'response': {
                    'code': 200,
                    'time': 0.1,
                    'headers': {},
                    'json': {'code': 0},
                    'text': '{"code":0}',
                },
                'cache_data': {'expected_code': 0},
            },
        )

    def test_verify_uses_response_and_cache_snapshot_without_persisting_results(self):
        queryset = SimpleNamespace(
            filter=lambda **_kwargs: SimpleNamespace(first=lambda: self.parameter),
        )
        test_setup = SimpleNamespace(
            test_data=self.FakeTestData(),
            test_object=None,
            close_db_connections=lambda: None,
        )
        with patch.object(
                ApiCaseDetailedParameter.objects,
                'select_related',
                return_value=queryset,
        ), patch(
            'src.apps.auto_api.services.base.assertion_verification.APIBaseTestSetup',
            return_value=test_setup,
        ):
            result = ApiAssertionVerificationService.verify(
                self.parameter.id,
                {
                    'ass_json_all': {'code': 0},
                    'ass_text_all': None,
                    'ass_jsonpath': [{
                        'assertion_type': 'cache',
                        'actual': '${{expected_code}}',
                        'method': 'p_is_equal_to',
                        'expect': 0,
                    }],
                    'ass_schema': None,
                    'ass_general': [],
                },
                test_env=0,
            )

        self.assertTrue(result['passed'])
        self.assertEqual(result['passed_count'], 2)
        self.assertEqual(result['failed_count'], 0)
        self.assertEqual(self.parameter.ass_jsonpath, [])


class ApiCaseDiagnosticMessageTests(SimpleTestCase):
    class FakeTestData:

        def __init__(self):
            self.cache = {}

        def replace(self, value):
            return value

        def set_cache(self, key, value):
            self.cache[key] = value

        def get_cache(self, key):
            return self.cache.get(key)

        def set_sql_cache(self, key, value):
            self.cache[key] = value

    class FakeConnection:

        def __init__(self, result):
            self.result = result

        def condition_execute(self, _sql):
            return self.result

    def make_case_parameter(self, *, sql_result=None, parameter=None, api_info=None):
        test_data = self.FakeTestData()
        test_setup = SimpleNamespace(
            test_data=test_data,
            test_object=None,
            get_db_connection=lambda _config: self.FakeConnection(sql_result),
        )
        parameter = parameter or SimpleNamespace(
            ass_json_all=None,
            ass_text_all=None,
            ass_schema=None,
        )
        api_info = api_info or SimpleNamespace(is_schema=0, ass_schema=None)
        return CaseParameter(test_setup, parameter, api_info, test_env=0)

    def test_response_json_extract_reports_empty_array_path(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__posterior_response(
                {'data': {'contract_texts': []}},
                [{'key': 'file_id', 'value': '$.data.contract_texts.0.file_id'}],
            )

        self.assertIn('响应JSON提取（第1项）失败', context.exception.msg)
        self.assertIn('缓存Key：【file_id】', context.exception.msg)
        self.assertIn('空数组', context.exception.msg)

    def test_posterior_sql_empty_query_result_reports_cache_key(self):
        case_parameter = self.make_case_parameter(sql_result=[])

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__posterior_sql([
                {
                    'key': 'user_id',
                    'value': 'select id from user where name = 1',
                    'datasource_alias': 2,
                    'test_envs': [],
                }
            ])

        self.assertIn('后置SQL处理失败（第1项', context.exception.msg)
        self.assertIn('缓存Key：【user_id】', context.exception.msg)
        self.assertIn('查询结果为空', context.exception.msg)

    def test_forced_wait_invalid_value_reports_allowed_range(self):
        with self.assertRaises(AutoApiError) as context:
            CaseParameter._CaseParameter__posterior_sleep('invalid')

        self.assertIn('强制等待配置错误', context.exception.msg)
        self.assertIn('0~32767', context.exception.msg)

    def test_json_consistency_reports_paths_and_value_types(self):
        parameter = SimpleNamespace(
            ass_json_all={'data': {'status': 1, 'id': 2}},
            ass_text_all=None,
            ass_schema=None,
        )
        case_parameter = self.make_case_parameter(parameter=parameter)

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_json_all(
                {'data': {'status': 0}},
                {'data': {'status': 1, 'id': 2}},
            )

        self.assertIn('JSON一致断言失败', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('$.data.status', context.exception.msg)
        self.assertIn('$.data.status', case_parameter.ass_result[0].ass_msg)
        self.assertIn('实际=0(int)', case_parameter.ass_result[0].ass_msg)
        self.assertIn('$.data.id', case_parameter.ass_result[0].ass_msg)

    def test_jsonpath_assertion_keeps_only_failure_reason_in_detail(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(
                ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 500}, text='{"code":500}'),
                [{'actual': '$.code', 'method': 'p_is_equal_to', 'expect': 200}],
            )

        self.assertIn('响应提取断言失败（第1项）：实际=500，预期=200', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('提取表达式：【$.code】', context.exception.msg)
        assertion_detail = case_parameter.ass_result[0].ass_msg
        self.assertIn('实际=500', assertion_detail)
        self.assertIn('预期=200', assertion_detail)
        self.assertNotIn('提取表达式', assertion_detail)
        self.assertEqual(case_parameter.ass_result[0].actual_source, '$.code')
        self.assertEqual(case_parameter.ass_result[0].actual, 500)
        self.assertEqual(case_parameter.ass_result[0].expect, 200)

    def test_jsonpath_assertion_reports_extraction_failure_path(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'data': {'items': []}},
            text='{"data":{"items":[]}}',
        )

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(response, [{
                'assertion_type': 'jsonpath',
                'actual': '$.data.items.0.id',
                'method': 'p_is_equal_to',
                'expect': 1,
            }])

        self.assertIn('JSONPath提取断言取值（第1项）失败', context.exception.msg)
        self.assertIn('表达式：【$.data.items.0.id】', context.exception.msg)
        self.assertIn('空数组', context.exception.msg)

    def test_jsonpath_assertion_reports_missing_field_clearly(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'data': {'items': [{
                'roleKey': 'admin',
                'roleName': '管理员',
                'builtin': False,
                'users': [],
                'departments': [],
                'agents': [],
            }]}},
            text='',
        )

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(response, [{
                'assertion_type': 'jsonpath',
                'actual': '$.data.items[0].appkey',
                'method': 'p_is_equal_to',
                'expect': 'admin',
            }])

        self.assertIn('JSONPath提取断言取值（第1项）失败', context.exception.msg)
        self.assertIn('JSONPath字段不存在', context.exception.msg)
        self.assertIn('父路径【$.data.items[0]】', context.exception.msg)
        self.assertIn('没有字段【appkey】', context.exception.msg)
        self.assertIn('当前对象可用字段：roleKey、roleName、builtin、users、departments、agents', context.exception.msg)
        self.assertIn('请将断言字段改为可用字段之一', context.exception.msg)

    def test_jsonpath_assertion_result_records_missing_field_clearly(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'data': {'items': [{
                'roleKey': 'admin',
                'roleName': '管理员',
                'builtin': False,
                'users': [],
                'departments': [],
                'agents': [],
            }]}},
            text='',
        )

        with self.assertRaises(AutoApiError):
            case_parameter._CaseParameter__ass_jsonpath(
                response,
                [{
                    'assertion_type': 'jsonpath',
                    'actual': '$.data.items[0].appkey',
                    'method': 'p_is_equal_to',
                    'expect': 'admin',
                }],
                continue_on_failure=True,
            )

        self.assertEqual(len(case_parameter.ass_result), 1)
        assertion_message = case_parameter.ass_result[0].ass_msg
        self.assertIn('JSONPath字段不存在', assertion_message)
        self.assertIn('父路径【$.data.items[0]】', assertion_message)
        self.assertIn('没有字段【appkey】', assertion_message)
        self.assertIn('请将断言字段改为可用字段之一', assertion_message)

    def test_general_assertion_uses_concise_error_and_keeps_detailed_result(self):
        case_parameter = self.make_case_parameter()
        assertions = [{
            'value': {
                'value': 'p_is_equal_to',
                'parameter': [
                    {'f': 'actual', 'v': 0},
                    {'f': 'expect', 'v': 1},
                ],
            },
        }]

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_general(assertions, assertions)

        self.assertIn('通用断言失败（第1项）：实际=0，预期=1', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('方法：【', context.exception.msg)
        assertion_detail = case_parameter.ass_result[0].ass_msg
        self.assertIn('方法：【', assertion_detail)
        self.assertIn('实际值：【0(int)】', assertion_detail)
        self.assertIn('预期值：【1(int)】', assertion_detail)

    def test_general_assertion_summary_truncates_long_values(self):
        case_parameter = self.make_case_parameter()
        actual = 'a' * 200
        expect = 'b' * 200
        assertions = [{
            'value': {
                'value': 'p_is_equal_to',
                'parameter': [
                    {'f': 'actual', 'v': actual},
                    {'f': 'expect', 'v': expect},
                ],
            },
        }]

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_general(assertions, assertions)

        self.assertLess(len(context.exception.msg), 260)
        self.assertEqual(context.exception.msg.count('（共200字符）'), 2)
        self.assertIn(actual, case_parameter.ass_result[0].ass_msg)
        self.assertIn(expect, case_parameter.ass_result[0].ass_msg)

    def test_text_consistency_reports_first_difference_and_lengths(self):
        parameter = SimpleNamespace(
            ass_json_all=None,
            ass_text_all='done',
            ass_schema=None,
        )
        case_parameter = self.make_case_parameter(parameter=parameter)

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_test_all('doing', 'done')

        self.assertIn('文本一致断言失败：实际=doing，预期=done', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('首次差异位于', context.exception.msg)
        self.assertIn('首次差异位于第【3】个字符', case_parameter.ass_result[0].ass_msg)
        self.assertIn('实际长度【5】', case_parameter.ass_result[0].ass_msg)

    def test_schema_assertion_reports_missing_field_path(self):
        schema = {
            'type': 'object',
            'required': ['contract_id'],
            'properties': {'contract_id': {'type': 'integer'}},
        }
        parameter = SimpleNamespace(
            ass_json_all=None,
            ass_text_all=None,
            ass_schema=schema,
        )
        case_parameter = self.make_case_parameter(parameter=parameter)
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='{}')

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_schema(response)

        self.assertIn('结构化断言失败', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('响应路径【$】缺少必填字段【contract_id】', context.exception.msg)
        self.assertIn('响应路径【$】缺少必填字段【contract_id】', case_parameter.ass_result[0].ass_msg)

    def test_schema_assertion_reports_invalid_schema_path(self):
        parameter = SimpleNamespace(
            ass_json_all=None,
            ass_text_all=None,
            ass_schema={'type': 'unknown-type'},
        )
        case_parameter = self.make_case_parameter(parameter=parameter)
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='{}')

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_schema(response)

        self.assertIn('结构化断言配置错误', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('Schema路径', context.exception.msg)
        self.assertIn('Schema路径', case_parameter.ass_result[0].ass_msg)

    def test_assertion_verification_collects_failures_from_all_categories(self):
        parameter = SimpleNamespace(
            ass_json_all={'code': 0},
            ass_text_all='expected text',
            ass_jsonpath=[{
                'assertion_type': 'jsonpath',
                'actual': '$.code',
                'method': 'p_is_equal_to',
                'expect': 0,
            }],
            ass_schema={
                'type': 'object',
                'required': ['data'],
            },
            ass_general=[{
                'value': {
                    'value': 'p_is_equal_to',
                    'parameter': [
                        {'f': 'actual', 'v': 1},
                        {'f': 'expect', 'v': 2},
                    ],
                },
            }],
        )
        case_parameter = self.make_case_parameter(parameter=parameter)
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 500}, text='actual text')

        results, status, error_message = case_parameter.verify_all_assertions(response)

        self.assertEqual(status, StatusEnum.FAIL.value)
        self.assertEqual(len(results), 5)
        self.assertTrue(all(item.status == StatusEnum.FAIL.value for item in results))
        self.assertIn('JSON一致断言失败', error_message)
        self.assertIn('文本一致断言失败', error_message)
        self.assertIn('响应提取断言失败', error_message)
        self.assertIn('结构化断言失败', error_message)
        self.assertIn('通用断言失败', error_message)

    def test_regular_assertion_execution_collects_all_failures(self):
        parameter = SimpleNamespace(
            ass_json_all=None,
            ass_text_all=None,
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
            ass_schema=None,
            ass_general=[],
        )
        case_parameter = self.make_case_parameter(parameter=parameter)
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
        self.assertIn('实际=500，预期=0', error_message)
        self.assertIn('实际=failed，预期=ok', error_message)
        self.assertEqual(results[0].actual_source, '$.code')
        self.assertEqual(results[1].actual_source, '$.status')
        self.assertIn('实际=500', results[0].ass_msg)
        self.assertIn('实际=failed', results[1].ass_msg)

    def test_or_group_failure_reports_relation_and_counts(self):
        case_parameter = self.make_case_parameter()

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(
                ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 500}, text='{"code":500}'),
                [
                    {
                        'group_name': '状态兼容',
                        'group_logic': 'OR',
                        'actual': '$.code',
                        'method': 'p_is_equal_to',
                        'expect': 200,
                    },
                    {
                        'group_name': '状态兼容',
                        'group_logic': 'OR',
                        'actual': '$.code',
                        'method': 'p_is_equal_to',
                        'expect': 201,
                    },
                ],
            )

        self.assertIn('或组【状态兼容】失败', context.exception.msg)
        self.assertIn('共2条，0条通过，2条失败', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('关系：【或】', context.exception.msg)
        self.assertTrue(any(item.group_logic == 'OR' and item.group_name == '状态兼容'
                            for item in case_parameter.ass_result))

    def test_regex_extract_assertion_uses_capture_group_then_asserts(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'contractId': '123456'},
            text='{"contractId":"123456"}',
        )

        case_parameter._CaseParameter__ass_jsonpath(response, [{
            'assertion_type': 'regex',
            'actual': r'"contractId":"(\d+)"',
            'method': 'p_is_equal_to',
            'expect': '123456',
        }])

        result = case_parameter.ass_result[0]
        self.assertEqual(result.actual, '123456')
        self.assertEqual(result.source_type, 'regex')
        self.assertIn('第1个捕获组', result.ass_msg)

    def test_regex_extract_no_match_can_be_asserted_as_none(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='done')

        case_parameter._CaseParameter__ass_jsonpath(response, [{
            'assertion_type': 'regex',
            'actual': r'error=(\w+)',
            'method': 'p_is_none',
            'expect': None,
        }])

        result = case_parameter.ass_result[0]
        self.assertIsNone(result.actual)
        self.assertIn('正则未匹配响应文本', result.ass_msg)

    def test_regex_extract_no_match_assertion_failure_is_explicit(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='done')

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(response, [{
                'assertion_type': 'regex',
                'actual': r'error=(\w+)',
                'method': 'p_is_equal_to',
                'expect': 'timeout',
            }])

        self.assertIn('响应提取断言失败（第1项）：实际=None，预期=timeout', context.exception.msg)
        self.assertIn('详情见断言结果', context.exception.msg)
        self.assertNotIn('正则未匹配响应文本', context.exception.msg)
        assertion_detail = case_parameter.ass_result[0].ass_msg
        self.assertIn('实际=None', assertion_detail)
        self.assertIn('预期=timeout', assertion_detail)
        self.assertNotIn('取值方式', assertion_detail)
        self.assertIsNone(case_parameter.ass_result[0].actual)
        self.assertEqual(case_parameter.ass_result[0].expect, 'timeout')

    def test_regex_extract_invalid_expression_reports_item(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='done')

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(response, [{
                'assertion_type': 'regex',
                'actual': r'(?<=a+)b',
                'method': 'p_is_equal_to',
                'expect': 'b',
            }])

        self.assertIn('响应提取断言配置错误（第1项）', context.exception.msg)
        self.assertIn('正则表达式', context.exception.msg)

    def test_missing_assertion_type_defaults_to_jsonpath(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={'code': 0}, text='{"code":0}')

        case_parameter._CaseParameter__ass_jsonpath(response, [{
            'actual': '$.code',
            'method': 'p_is_equal_to',
            'expect': 0,
        }])

        self.assertEqual(case_parameter.ass_result[0].source_type, 'jsonpath')

    def test_legacy_regex_method_is_no_longer_executable(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(
            code=200,
            time=0.1,
            headers={},
            json={'name': 'order-10001'},
            text='{"name":"order-10001"}',
        )

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(response, [{
                'actual': '$.name',
                'method': 'p_matches',
                'expect': r'order-\d+',
            }])

        self.assertIn('断言方法【p_matches】不存在', context.exception.msg)

    def test_cache_assertion_resolves_expression_then_asserts(self):
        case_parameter = self.make_case_parameter()
        case_parameter.test_setup.test_data.set_cache('order_id', 10001)
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='done')

        case_parameter._CaseParameter__ass_jsonpath(response, [{
            'assertion_type': 'cache',
            'actual': '${{order_id}}',
            'method': 'p_is_equal_to',
            'expect': 10001,
        }])

        result = case_parameter.ass_result[0]
        self.assertEqual(result.actual, 10001)
        self.assertEqual(result.source_type, 'cache')
        self.assertIn('当前用例运行缓存', result.ass_msg)

    def test_cache_assertion_reports_missing_cache_key(self):
        case_parameter = self.make_case_parameter()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='done')

        with self.assertRaises(AutoApiError) as context:
            case_parameter._CaseParameter__ass_jsonpath(response, [{
                'assertion_type': 'cache',
                'actual': '${{missing_id}}',
                'method': 'p_is_not_none',
                'expect': None,
            }])

        self.assertIn('缓存值断言取值失败（第1项', context.exception.msg)
        self.assertIn('缓存Key：【missing_id】', context.exception.msg)
        self.assertIn('不存在该Key或其值为空', context.exception.msg)

    def test_serializer_rejects_incomplete_posterior_extract(self):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaises(AutoApiError) as context:
            serializer.validate_posterior_response([{'key': 'file_id', 'value': ''}])

        self.assertIn('响应JSON提取第1项的JSONPath不能为空', context.exception.msg)

    def test_serializer_rejects_unknown_assertion_method(self):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaises(AutoApiError) as context:
            serializer.validate_ass_jsonpath([
                {'actual': '$.code', 'method': 'not_exists', 'expect': '200'}
            ])

        self.assertIn('断言方法【not_exists】不存在', context.exception.msg)

    def test_serializer_defaults_missing_assertion_type_to_jsonpath(self):
        serializer = ApiCaseDetailedParameterSerializers()

        result = serializer.validate_ass_jsonpath([{
            'actual': '$.code',
            'method': 'p_is_equal_to',
            'expect': '0',
        }])

        self.assertEqual(result[0]['assertion_type'], 'jsonpath')

    def test_serializer_rejects_invalid_regex_assertion(self):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaises(AutoApiError) as context:
            serializer.validate_ass_jsonpath([{
                'assertion_type': 'regex',
                'actual': r'(?<=a+)b',
                'method': 'p_is_equal_to',
                'expect': 'b',
            }])

        self.assertIn('正则表达式不合法', context.exception.msg)

    def test_serializer_rejects_cache_assertion_without_expression_wrapper(self):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaises(AutoApiError) as context:
            serializer.validate_ass_jsonpath([{
                'assertion_type': 'cache',
                'actual': 'order_id',
                'method': 'p_is_equal_to',
                'expect': '10001',
            }])

        self.assertIn('必须使用完整的${{key}}格式', context.exception.msg)

    def test_serializer_rejects_forced_wait_out_of_range(self):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaises(AutoApiError) as context:
            serializer.validate_posterior_sleep(32768)

        self.assertIn('超出允许范围0~32767秒', context.exception.msg)

    def test_serializer_rejects_non_integer_forced_wait(self):
        serializer = ApiCaseDetailedParameterSerializers()

        with self.assertRaises(AutoApiError) as context:
            serializer.validate_posterior_sleep('30')

        self.assertIn('必须是0~32767之间的整数', context.exception.msg)
