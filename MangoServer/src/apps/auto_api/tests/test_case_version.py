import json
import os
from unittest.mock import MagicMock, patch

import jwt
from django.conf import settings
from django.test import TestCase
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiCaseRelease,
    ApiCaseRevision,
    ApiHeaders,
    ApiInfo,
    ApiInfoRevision,
)
from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import (
    ExecutionResult,
    ProductModule,
    Project,
    ProjectProduct,
    TestSuite,
    TestSuiteDetails,
)
from src.apps.user.models import User
from src.apps.user.services.authorization.permission import PermissionMenuService


class ApiCaseRevisionServiceTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='版本测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='开放平台')
        self.module = ProductModule.objects.create(project_product=self.product, name='订单模块')
        self.owner = User.objects.create(
            name='版本负责人',
            username='case_version_owner',
            password='pwd',
            is_super_admin=True,
        )
        self.product.owners.add(self.owner)
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='创建订单',
            url='/open-apis/contracts',
            method=1,
            headers={'X-Trace': '{{ trace_id }}'},
            protocol_type='http',
            body_type='json',
            body_config={'json': {'contract_name': '${contract_name}'}},
            status=1,
            result_data={'response': {'id': 99}},
        )
        self.case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='订单创建链路',
            case_people=self.owner,
            case_flow='1',
            status=1,
        )
        self.step = ApiCaseDetailed.objects.create(
            case=self.case,
            api_info=self.api_info,
            case_sort=1,
            status=1,
            error_message='旧执行错误',
        )
        self.parameter = ApiCaseDetailedParameter.objects.create(
            case_detailed=self.step,
            name='创建订单成功',
            body_config={'json': {'contract_name': '${contract_name}'}},
            ass_general=[{
                'method': 'p_equals',
                'actual': '${{status_code}}',
                'expect': 200,
            }],
            status=1,
            result_data={'response': {'id': 99}},
        )
        self.token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

    def test_record_current_captures_aggregate_and_locks_api_revision(self):
        revision = ApiCaseRevisionService.record_current(
            self.case.id,
            operator_id=self.owner.id,
            source='test',
            summary='初始化版本',
        )

        self.assertEqual(revision.revision_no, 1)
        self.assertEqual(revision.payload['name'], '订单创建链路')
        self.assertEqual(revision.payload['steps'][0]['parameters'][0]['name'], '创建订单成功')
        self.assertNotIn('status', revision.payload)
        self.assertNotIn('prepublished_revision', revision.payload['api_case'])
        self.assertNotIn('status', revision.payload['steps'][0])
        self.assertNotIn('error_message', revision.payload['steps'][0])
        self.assertNotIn('result_data', revision.payload['steps'][0]['parameters'][0])

        api_revision_id = revision.payload['steps'][0]['api_info_revision_id']
        api_revision = ApiInfoRevision.objects.get(id=api_revision_id)
        self.assertEqual(api_revision.api_info_id, self.api_info.id)
        self.assertEqual(api_revision.payload['url'], '/open-apis/contracts')
        self.assertNotIn('status', api_revision.payload)
        self.assertNotIn('result_data', api_revision.payload)

    def test_record_current_uses_step_pinned_api_info_revision(self):
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        pinned_revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url'])
        ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        self.step.pinned_api_info_revision = pinned_revision
        self.step.save(update_fields=['pinned_api_info_revision'])

        case_revision = ApiCaseRevisionService.record_current(self.case.id, source='test')

        self.assertEqual(case_revision.payload['steps'][0]['api_info_revision_id'], pinned_revision.id)
        self.assertEqual(pinned_revision.payload['url'], '/open-apis/contracts')

    def test_record_current_reuses_revision_when_payload_is_unchanged(self):
        first = ApiCaseRevisionService.record_current(self.case.id, source='test')
        second = ApiCaseRevisionService.record_current(self.case.id, source='test')

        self.assertEqual(second.id, first.id)
        self.assertEqual(ApiCaseRevision.objects.filter(api_case=self.case).count(), 1)
        self.assertEqual(ApiInfoRevision.objects.filter(api_info=self.api_info).count(), 1)

    def test_record_current_keeps_only_one_publishable_unpublished_candidate(self):
        first = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.case.name = '订单创建链路 V2'
        self.case.save(update_fields=['name', 'update_time'])

        second = ApiCaseRevisionService.record_current(self.case.id, source='test')

        with self.assertRaises(AutoApiError) as first_context:
            ApiCaseRevisionService.submit_prepublication(self.case.id, first.id)
        self.assertEqual(first_context.exception.code, 31213)
        release = ApiCaseRevisionService.submit_prepublication(self.case.id, second.id)
        self.assertEqual(release.revision_id, second.id)
        self.assertEqual(release.status, ApiCaseReleaseStatusEnum.PREPUBLISHED.value)

    def test_record_current_rejects_changes_while_candidate_is_prepublished(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)
        self.case.name = '预发布期间的编辑内容'
        self.case.save(update_fields=['name', 'update_time'])

        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.record_current(self.case.id, source='test')

        self.assertEqual(context.exception.code, 31212)

    def test_superseded_revision_cannot_be_submitted_to_prepublication(self):
        first = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.case.name = '订单创建链路 V2'
        self.case.save(update_fields=['name', 'update_time'])
        second = ApiCaseRevisionService.record_current(self.case.id, source='test')

        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.submit_prepublication(self.case.id, first.id)

        self.assertEqual(context.exception.code, 31213)
        self.assertFalse(ApiCaseRelease.objects.filter(revision_id=second.id).exists())

    def test_delete_unpublished_revision_detaches_historical_report_reference(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        suite = TestSuite.objects.create(
            id=987654321,
            project_product=self.product,
            test_env=0,
            user=self.owner,
            status=TaskEnum.FAIL.value,
            is_notice=0,
        )
        detail = TestSuiteDetails.objects.create(
            test_suite=suite,
            type=TestCaseTypeEnum.API.value,
            project_product=self.product,
            test_env=0,
            case_id=self.case.id,
            case_name=self.case.name,
            status=TaskEnum.FAIL.value,
            retry=0,
            api_case_revision=revision,
            config_checksum=revision.checksum,
        )

        result = ApiCaseRevisionService.delete_unpublished_revision(
            self.case.id,
            revision.id,
        )

        detail.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(id=revision.id).exists())
        self.assertIsNone(detail.api_case_revision_id)
        self.assertIsNone(detail.config_checksum)
        self.assertEqual(result['detached_report_detail_count'], 1)

    def test_model_crud_config_change_only_updates_current_editing_state(self):
        from src.apps.auto_api.api.views.api_case import ApiCaseCRUD

        with self.captureOnCommitCallbacks(execute=True):
            ApiCaseCRUD.inside_put(self.case.id, {
                'id': self.case.id,
                'name': '订单创建链路-已编辑',
            })

        self.case.refresh_from_db()
        self.assertEqual(self.case.name, '订单创建链路-已编辑')
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

    def test_model_crud_does_not_call_revision_creation(self):
        from src.apps.auto_api.api.views.api_case import ApiCaseCRUD

        with patch.object(
                ApiCaseRevisionService,
                'record_current',
                side_effect=RuntimeError('revision failed'),
        ) as record_current:
            ApiCaseCRUD.inside_put(self.case.id, {
                'id': self.case.id, 'name': '订单创建链路-已编辑',
            })

        self.case.refresh_from_db()
        self.assertEqual(self.case.name, '订单创建链路-已编辑')
        record_current.assert_not_called()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

    def test_revision_requires_latest_current_editing_run_to_succeed(self):
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.ensure_current_editing_run_succeeded(self.case.id)

        ExecutionResult.objects.create(
            source_type='page',
            target_type='api_case',
            target_id=self.case.id,
            status=StatusEnum.FAIL.value,
        )
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.ensure_current_editing_run_succeeded(self.case.id)

        ExecutionResult.objects.create(
            source_type='mcp',
            target_type='api_case',
            target_id=self.case.id,
            status=StatusEnum.SUCCESS.value,
        )
        ApiCaseRevisionService.ensure_current_editing_run_succeeded(self.case.id)

        self.parameter.name = '创建订单成功 V2'
        self.parameter.save(update_fields=['name', 'update_time'])
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.ensure_current_editing_run_succeeded(self.case.id)

    def test_add_step_only_updates_current_editing_state(self):
        response = self.client.post(
            '/api/api/case/detailed',
            data=json.dumps({
                'case': self.case.id,
                'api_info': self.api_info.id,
                'case_sort': 2,
                'module': self.module.id,
                'parent_id': self.case.id,
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], 200)
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertEqual(ApiCaseDetailed.objects.filter(case=self.case).count(), 2)

    def test_add_step_rolls_back_step_when_default_parameter_creation_fails(self):
        with patch(
                'src.apps.auto_api.api.views.api_case_detailed_parameter.'
                'ApiCaseDetailedParameterCRUD.inside_post',
                side_effect=RuntimeError('parameter failed'),
        ):
            response = self.client.post(
                '/api/api/case/detailed',
                data=json.dumps({
                    'case': self.case.id,
                    'api_info': self.api_info.id,
                    'case_sort': 2,
                    'module': self.module.id,
                    'parent_id': self.case.id,
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=self.token,
            )

        self.assertNotEqual(response.json()['code'], 200)
        self.assertEqual(ApiCaseDetailed.objects.filter(case=self.case).count(), 1)
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

    def test_add_parameter_refreshes_case_flow_without_revision(self):
        response = self.client.post(
            '/api/api/case/detailed/parameter',
            data=json.dumps({
                'case_detailed': self.step.id,
                'api_info': self.api_info.id,
                'name': '创建订单边界场景',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], 200)
        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertIn('创建订单边界场景', self.case.case_flow)

    def test_update_parameter_refreshes_case_flow_without_revision(self):
        response = self.client.put(
            '/api/api/case/detailed/parameter',
            data=json.dumps({
                'id': self.parameter.id,
                'name': '创建订单成功 V2',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], 200)
        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertIn('创建订单成功 V2', self.case.case_flow)

    def test_delete_parameter_updates_editing_state_without_revision(self):
        with patch.object(
                ApiCaseRevisionService,
                'record_current',
                side_effect=RuntimeError('revision failed'),
        ) as record_current:
            response = self.client.delete(
                f'/api/api/case/detailed/parameter?id={self.parameter.id}',
                HTTP_AUTHORIZATION=self.token,
            )

        self.assertEqual(response.json()['code'], 200)
        self.case.refresh_from_db()
        record_current.assert_not_called()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertFalse(ApiCaseDetailedParameter.objects.filter(id=self.parameter.id).exists())

    def test_copy_parameter_updates_editing_state_without_revision(self):
        response = self.client.post(
            '/api/api/case/detailed/parameter/copy',
            data=json.dumps({
                'id': self.parameter.id,
                'name': '创建订单成功副本',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], 200)
        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertIn('创建订单成功副本', self.case.case_flow)
        self.assertEqual(ApiCaseDetailedParameter.objects.filter(case_detailed=self.step).count(), 2)

    def test_mcp_add_step_helper_updates_editing_state_without_revision(self):
        from src.interfaces.mcp.tools.api.helper_parts.execution import _create_case_step

        result = _create_case_step(self.case.id, self.api_info.id, case_sort=2)

        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertTrue(ApiCaseDetailedParameter.objects.filter(id=result['default_parameter_id']).exists())

    def test_mcp_complete_case_creation_keeps_case_in_editing_state(self):
        from src.interfaces.mcp.tools.api.case import register_case_tools
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_case_tools(registry)
        api_revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        ApiInfoRevisionService.publish(
            self.api_info.id,
            api_revision.id,
            publisher_id=self.owner.id,
        )
        with patch.dict(os.environ, {'MANGO_MCP_ALLOW_USER_ID_AUTH': '1'}):
            result = registry.tools['create_complete_api_case'](
                project_product_id=self.product.id,
                module_id=self.module.id,
                case_name='MCP 完整版本用例',
                api={'api_info_id': self.api_info.id},
                scenarios=[
                    {'name': 'MCP 正常场景', 'body_config': {'json': {'version': 1}}},
                    {'name': 'MCP 边界场景', 'body_config': {'json': {'version': 2}}},
                ],
                case_people_id=self.owner.id,
                user_id=self.owner.id,
            )

        self.assertTrue(result['success'], result)
        created_case = ApiCase.objects.get(id=result['data']['case_id'])
        revisions = ApiCaseRevision.objects.filter(api_case=created_case)
        self.assertEqual(revisions.count(), 0)
        self.assertIsNone(result['data']['revision_id'])
        created_step = ApiCaseDetailed.objects.get(case=created_case)
        self.assertEqual(
            ApiCaseDetailedParameter.objects.filter(case_detailed=created_step).count(),
            2,
        )

    def test_mcp_complete_case_run_uses_current_editing_state(self):
        from src.interfaces.mcp.tools.api.case import register_case_tools
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_case_tools(registry)
        api_revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        ApiInfoRevisionService.publish(
            self.api_info.id,
            api_revision.id,
            publisher_id=self.owner.id,
        )
        with patch.dict(os.environ, {'MANGO_MCP_ALLOW_USER_ID_AUTH': '1'}), \
                patch('src.interfaces.mcp.tools.api.case.TestCase') as runtime_case:
            runtime_case.return_value.test_case.return_value.model_dump.return_value = {'status': 1}
            result = registry.tools['create_complete_api_case'](
                project_product_id=self.product.id,
                module_id=self.module.id,
                case_name='MCP 创建后执行版本用例',
                api={'api_info_id': self.api_info.id},
                scenarios=[
                    {'name': 'MCP 创建后执行场景', 'body_config': {'json': {'version': 1}}},
                ],
                case_people_id=self.owner.id,
                run_after_create=True,
                test_env_id=0,
                user_id=self.owner.id,
            )

        self.assertTrue(result['success'], result)
        created_case = ApiCase.objects.get(id=result['data']['case_id'])
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=created_case).exists())
        self.assertIsNone(result['data']['revision_id'])
        runtime_case.assert_called_once_with(
            user_id=self.owner.id,
            test_env=0,
            case_id=created_case.id,
        )

    def test_mcp_delete_step_updates_editing_state_without_revision(self):
        from src.interfaces.mcp.tools.api.delete import register_delete_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_delete_tools(registry)
        with patch(
                'src.interfaces.mcp.tools.api.delete.validate_dangerous_action_confirmation',
                return_value=None,
        ):
            result = registry.tools['delete_api_case_step'](self.step.id)

        self.assertTrue(result['success'], result)
        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertFalse(ApiCaseDetailed.objects.filter(id=self.step.id).exists())

    def test_mcp_delete_scenario_updates_editing_state_without_revision(self):
        from src.interfaces.mcp.tools.api.delete import register_delete_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_delete_tools(registry)
        with patch(
                'src.interfaces.mcp.tools.api.delete.validate_dangerous_action_confirmation',
                return_value=None,
        ):
            result = registry.tools['delete_api_case_scenario'](self.parameter.id)

        self.assertTrue(result['success'], result)
        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertFalse(ApiCaseDetailedParameter.objects.filter(id=self.parameter.id).exists())

    def test_mcp_sort_steps_does_not_call_revision_creation(self):
        from src.interfaces.mcp.tools.api.case import register_case_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_case_tools(registry)
        with patch.object(
                ApiCaseRevisionService,
                'record_current',
                side_effect=RuntimeError('revision failed'),
        ) as record_current:
            result = registry.tools['sort_api_case_steps'](
                self.case.id,
                [{'step_id': self.step.id, 'case_sort': 9}],
            )

        self.assertTrue(result['success'], result)
        self.step.refresh_from_db()
        self.assertEqual(self.step.case_sort, 9)
        record_current.assert_not_called()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

    def test_mcp_refresh_step_does_not_call_revision_creation(self):
        from src.interfaces.mcp.tools.api.case import register_case_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_case_tools(registry)
        original_body = self.parameter.body_config
        self.api_info.body_config = {'json': {'version': 2}}
        self.api_info.save(update_fields=['body_config', 'update_time'])

        with patch.object(
                ApiCaseRevisionService,
                'record_current',
                side_effect=RuntimeError('revision failed'),
        ) as record_current:
            result = registry.tools['refresh_api_case_step_from_api_info'](self.step.id)

        self.assertTrue(result['success'], result)
        self.parameter.refresh_from_db()
        self.assertNotEqual(self.parameter.body_config, original_body)
        record_current.assert_not_called()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

    def test_page_step_sort_rejects_steps_from_different_cases_atomically(self):
        another_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='另一个排序用例',
            case_people=self.owner,
            case_flow='1',
            status=1,
        )
        another_step = ApiCaseDetailed.objects.create(
            case=another_case,
            api_info=self.api_info,
            case_sort=1,
            status=1,
        )
        ApiCaseDetailedParameter.objects.create(
            case_detailed=another_step,
            name='另一个排序场景',
            status=1,
        )

        response = self.client.put(
            '/api/api/case/detailed/sort',
            data=json.dumps({
                'case_sort_list': [
                    {'id': self.step.id, 'case_sort': 9},
                    {'id': another_step.id, 'case_sort': 8},
                ],
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertNotEqual(response.json()['code'], 200)
        self.step.refresh_from_db()
        another_step.refresh_from_db()
        self.assertEqual(self.step.case_sort, 1)
        self.assertEqual(another_step.case_sort, 1)
        self.assertFalse(ApiCaseRevision.objects.exists())

    def test_mcp_data_factory_changes_only_update_current_editing_state(self):
        from src.apps.data_factory.models import DataFactoryEntity, DataFactoryTemplate
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        from src.interfaces.mcp.tools.data_factory.case_config import register_case_config_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        entity = DataFactoryEntity.objects.create(
            project_product=self.product,
            module=self.module,
            name='MCP 数据工厂实体',
            table_name='contract',
        )
        template = DataFactoryTemplate.objects.create(
            project_product=self.product,
            module=self.module,
            entity=entity,
            name='MCP 数据工厂模板',
        )
        registry = ToolRegistry()
        register_case_config_tools(registry)

        bind_result = registry.tools['bind_data_factory_to_case_source'](
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
            source_id=self.case.id,
            template_id=template.id,
            name='contract',
        )
        self.assertTrue(bind_result['success'], bind_result)
        config_id = bind_result['data']['id']
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

        update_result = registry.tools['update_data_factory_case_config'](
            config_id,
            field_overrides={'version': 2},
        )
        self.assertTrue(update_result['success'], update_result)
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())

        sort_result = registry.tools['sort_data_factory_case_configs'](
            DataFactoryCaseSourceTypeEnum.API_CASE.value,
            [{'config_id': config_id, 'sort': 9}],
        )
        self.assertTrue(sort_result['success'], sort_result)
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        latest = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.assertEqual(latest.payload['data_factory_configs'][0]['sort'], 9)
        self.assertEqual(latest.payload['unsupported_dependency_types'], ['data_factory_template'])

    def test_gray_scope_replace_only_updates_current_editing_state(self):
        from src.apps.gray_config.enums import (
            GrayCaseScopeEnum,
            GrayCaseTypeEnum,
            GrayConfigTypeEnum,
        )
        from src.apps.gray_config.models import GrayFeature
        from src.apps.gray_config.services.case_config import GrayCaseConfigService

        feature = GrayFeature.objects.create(
            gray_code='GRAY-REVISION-TRACKING',
            config_type=GrayConfigTypeEnum.CODE.value,
            project_product=self.product,
            module=self.module,
            name='灰度版本追踪',
            feature_key='contract.revision',
            enable_code='def gray(context):\n    return True',
        )
        scope = {
            'case_type': GrayCaseTypeEnum.API.value,
            'scope': GrayCaseScopeEnum.CASE.value,
            'api_case': self.case.id,
        }

        GrayCaseConfigService.replace_scope_configs(
            scope,
            [{'gray_feature': feature.id, 'target_value': 'v2'}],
            user=self.owner,
        )
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        first_revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.assertEqual(first_revision.payload['unsupported_dependency_types'], ['gray_config'])

        GrayCaseConfigService.replace_scope_configs(scope, [], user=self.owner)
        self.assertEqual(ApiCaseRevision.objects.filter(api_case=self.case).count(), 1)
        second_revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.assertEqual(second_revision.payload['unsupported_dependency_types'], [])

    def test_gray_config_generic_crud_only_updates_current_editing_state(self):
        from src.apps.gray_config.enums import (
            GrayCaseScopeEnum,
            GrayCaseTypeEnum,
            GrayConfigTypeEnum,
        )
        from src.apps.gray_config.models import GrayFeature
        from src.apps.gray_config.api.views.case_config import AutomationCaseGrayConfigCRUD

        feature = GrayFeature.objects.create(
            gray_code='GRAY-GENERIC-CRUD',
            config_type=GrayConfigTypeEnum.CODE.value,
            project_product=self.product,
            module=self.module,
            name='灰度通用 CRUD',
            feature_key='contract.generic',
            enable_code='def gray(context):\n    return True',
        )

        AutomationCaseGrayConfigCRUD.inside_post({
            'case_type': GrayCaseTypeEnum.API.value,
            'scope': GrayCaseScopeEnum.CASE.value,
            'api_case': self.case.id,
            'gray_feature': feature.id,
            'target_value': 'v2',
        })

        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.assertEqual(revision.payload['unsupported_dependency_types'], ['gray_config'])

    def test_mcp_create_scenario_updates_editing_state_without_revision(self):
        from src.interfaces.mcp.tools.api.scenario import register_scenario_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_scenario_tools(registry)
        result = registry.tools['create_api_case_scenario'](
            self.step.id,
            'MCP 新增场景',
            body_config={'json': {'version': 2}},
        )

        self.assertTrue(result['success'], result)
        self.case.refresh_from_db()
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=self.case).exists())
        self.assertIn('MCP 新增场景', self.case.case_flow)
        self.assertEqual(ApiCaseDetailedParameter.objects.filter(case_detailed=self.step).count(), 2)

    def test_copy_case_creates_only_current_editing_state(self):
        response = self.client.post(
            '/api/api/case/copy',
            data=json.dumps({'case_id': self.case.id}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], 200)
        copied_case = ApiCase.objects.get(id=response.json()['data']['id'])
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=copied_case).exists())
        self.assertEqual(ApiCaseDetailed.objects.filter(case=copied_case).count(), 1)
        self.assertIn(self.parameter.name, copied_case.case_flow)

    def test_copy_case_does_not_copy_prepublication_state(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)

        response = self.client.post(
            '/api/api/case/copy',
            data=json.dumps({'case_id': self.case.id}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.json()['code'], 200)
        copied_case = ApiCase.objects.get(id=response.json()['data']['id'])
        self.assertFalse(ApiCaseRevision.objects.filter(api_case=copied_case).exists())
        self.assertTrue(
            ApiCaseRelease.objects.filter(
                revision=revision,
                status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
            ).exists()
        )

    def test_published_v1_remains_current_while_v2_is_draft(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v1 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
            release_note='线上稳定版本',
        )

        self.parameter.body_config = {'json': {'contract_name': '${contract_name}', 'version': 2}}
        self.parameter.save(update_fields=['body_config', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.case.id, source='test')

        state = ApiCaseRevisionService.get_publication_state(self.case.id)
        selection = ApiCaseRevisionService.resolve_current_published(self.case.id)

        self.assertEqual(release_v1.version_label, 'V1')
        self.assertEqual(state.publication_status, 'published')
        self.assertTrue(state.has_unpublished_changes)
        self.assertEqual(state.published_revision_id, revision_v1.id)
        self.assertEqual(state.current_revision_id, revision_v2.id)
        self.assertEqual(selection.case_revision_id, revision_v1.id)
        self.assertEqual(selection.case_release_id, release_v1.id)

    def test_unpublished_api_revision_does_not_change_case_publication_state(self):
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService

        api_revision_v1 = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        ApiInfoRevisionService.publish(
            self.api_info.id,
            api_revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.step.pinned_api_info_revision = None
        self.step.save(update_fields=['pinned_api_info_revision', 'update_time'])
        case_revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService._publish_revision(
            self.case.id,
            case_revision.id,
            publisher_id=self.owner.id,
        )

        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])
        ApiInfoRevisionService.record_current(self.api_info.id, source='test')

        state = ApiCaseRevisionService.get_publication_state(self.case.id)

        self.assertEqual(state.publication_status, ApiCaseRevisionService.PUBLICATION_PUBLISHED)
        self.assertFalse(state.has_unpublished_changes)

    def test_publishing_v2_switches_current_release_without_mutating_v1(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v1 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        v1_checksum = revision_v1.checksum

        self.case.name = '订单创建链路 V2'
        self.case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )

        release_v1.refresh_from_db()
        revision_v1.refresh_from_db()
        self.assertFalse(release_v1.is_current)
        self.assertTrue(release_v2.is_current)
        self.assertEqual(release_v2.version_label, 'V2')
        self.assertEqual(revision_v1.checksum, v1_checksum)
        self.assertEqual(revision_v1.payload['name'], '订单创建链路')
        self.assertEqual(ApiCaseRelease.objects.filter(api_case=self.case).count(), 2)

    def test_unpublish_removes_current_release_without_changing_history(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        result = ApiCaseRevisionService.unpublish(self.case.id, release.id)

        revision.refresh_from_db()
        self.assertFalse(result.is_current)
        self.assertEqual(result.status, ApiCaseRelease.STATUS_DEPRECATED)
        self.assertEqual(revision.checksum, ApiCaseRevisionService.checksum(revision.payload))
        state = ApiCaseRevisionService.get_publication_state(self.case.id)
        self.assertEqual(state.publication_status, ApiCaseRevisionService.PUBLICATION_UNPUBLISHED)
        self.assertIsNone(state.published_release_id)
        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.resolve_current_published(self.case.id)
        self.assertEqual(context.exception.code, 1125)

    def test_unpublish_rejects_stale_or_non_current_release(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )
        ApiCaseRevisionService.unpublish(self.case.id, release.id)

        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.unpublish(self.case.id, release.id)

        self.assertEqual(context.exception.code, 1162)

    def test_historical_revision_loader_does_not_read_mutated_current_configuration(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v1 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )

        self.case.name = '当前草稿 V2'
        self.case.save(update_fields=['name', 'update_time'])
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])
        self.parameter.body_config = {'json': {'contract_name': 'v2'}}
        self.parameter.save(update_fields=['body_config', 'update_time'])

        selection = ApiCaseRevisionService.resolve_revision(
            self.case.id,
            revision_v1.id,
            release_id=release_v1.id,
        )
        aggregate = ApiCaseRevisionService.load_execution_revision(selection.case_revision_id)

        self.assertEqual(aggregate.api_case.name, '订单创建链路')
        self.assertEqual(aggregate.steps[0].api_info.url, '/open-apis/contracts')
        self.assertEqual(
            aggregate.parameters_for_step(aggregate.steps[0])[0].body_config,
            {'json': {'contract_name': '${contract_name}'}},
        )
        self.assertEqual(selection.case_release_id, release_v1.id)
        self.assertEqual(selection.checksum, revision_v1.checksum)

    def test_historical_revision_uses_frozen_shared_headers_without_current_queries(self):
        from src.apps.auto_api.services.execution.base.case_base import CaseBase
        from src.apps.auto_api.services.execution.base.case_parameter import CaseParameter

        case_header = ApiHeaders.objects.create(
            project_product=self.product,
            key='X-Case-Version',
            value='{{ case_header_v1 }}',
            status=1,
        )
        scenario_header = ApiHeaders.objects.create(
            project_product=self.product,
            key='X-Scenario-Version',
            value='{{ scenario_header_v1 }}',
            status=1,
        )
        self.case.front_headers = [case_header.id]
        self.case.save(update_fields=['front_headers', 'update_time'])
        self.parameter.headers = [scenario_header.id]
        self.parameter.save(update_fields=['headers', 'update_time'])

        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        case_header.value = '{{ case_header_v2 }}'
        case_header.save(update_fields=['value', 'update_time'])
        scenario_header.value = '{{ scenario_header_v2 }}'
        scenario_header.save(update_fields=['value', 'update_time'])

        aggregate = ApiCaseRevisionService.load_execution_revision(revision_v1.id)
        frozen_parameter = aggregate.parameters_for_step(aggregate.steps[0])[0]

        self.assertEqual(
            revision_v1.payload['resolved_front_headers'],
            {'X-Case-Version': '{{ case_header_v1 }}'},
        )
        self.assertEqual(
            revision_v1.payload['steps'][0]['parameters'][0]['resolved_headers'],
            {'X-Scenario-Version': '{{ scenario_header_v1 }}'},
        )
        with patch(
                'src.apps.auto_api.services.execution.base.case_base.CaseDataFactory',
        ), patch.object(
            ApiHeaders.objects,
            'filter',
            side_effect=AssertionError('历史版本不应读取当前共享请求头'),
        ):
            case_base = CaseBase(MagicMock(), aggregate.api_case)
            case_base.case_front_main()
            resolved_parameter_headers = CaseParameter(
                MagicMock(),
                frozen_parameter,
                aggregate.steps[0].api_info,
            ).headers(frozen_parameter, case_base.case_headers)

        self.assertEqual(case_base.case_headers, {'X-Case-Version': '{{ case_header_v1 }}'})
        self.assertEqual(
            resolved_parameter_headers,
            {'X-Scenario-Version': '{{ scenario_header_v1 }}'},
        )

    def test_unfrozen_data_factory_revision_fails_closed_and_sort_only_updates_editing_state(self):
        from src.apps.data_factory.models import (
            DataFactoryCaseConfig,
            DataFactoryEntity,
            DataFactoryTemplate,
        )
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum

        entity = DataFactoryEntity.objects.create(
            project_product=self.product,
            module=self.module,
            name='订单实体',
            table_name='contract',
        )
        template = DataFactoryTemplate.objects.create(
            project_product=self.product,
            module=self.module,
            entity=entity,
            name='订单模板 V1',
        )
        config = DataFactoryCaseConfig.objects.create(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
            source_id=self.case.id,
            template=template,
            name='case_contract',
            field_overrides={'contract_version': 1},
            status=1,
        )
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        config.field_overrides = {'contract_version': 2}
        config.save(update_fields=['field_overrides', 'update_time'])
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.load_execution_revision(revision_v1.id)

        response = self.client.put(
            '/api/api/case/data-factory/sort',
            data=json.dumps({'case_sort_list': [{'id': config.id, 'sort': 9}]}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )
        self.assertEqual(response.json()['code'], 200)
        self.assertEqual(ApiCaseRevision.objects.filter(api_case=self.case).count(), 1)
        revision_v2 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.assertNotEqual(revision_v2.id, revision_v1.id)
        self.assertEqual(revision_v2.payload['data_factory_configs'][0]['sort'], 9)

    def test_runtime_test_case_uses_revision_aggregate(self):
        from src.apps.auto_api.services.execution.cases.test_case import TestCase as RuntimeTestCase

        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.case.name = '当前草稿 V2'
        self.case.save(update_fields=['name', 'update_time'])
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])

        with patch(
                'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                return_value=15,
        ):
            runtime_case = RuntimeTestCase(
                user_id=self.owner.id,
                test_env=0,
                case_id=self.case.id,
                revision_id=revision_v1.id,
            )

        steps = runtime_case.get_case_detailed_queryset(self.case.id, None)
        self.assertEqual(runtime_case.api_case.name, '订单创建链路')
        self.assertEqual(steps[0].api_info.url, '/open-apis/contracts')
        self.assertEqual(runtime_case.get_parameters_for_step(steps[0])[0].name, '创建订单成功')
        self.assertEqual(runtime_case.api_case_result.case_revision_id, revision_v1.id)

        runtime_case.trace_recorder.finish_trace({'status': 1, 'steps_count': 1})
        trace = runtime_case.trace_recorder.trace
        trace.refresh_from_db()
        self.assertEqual(trace.summary['case_revision_id'], str(revision_v1.id))
        self.assertEqual(trace.summary['config_checksum'], revision_v1.checksum)
        self.assertEqual(trace.summary['status'], '1')
        self.assertEqual(
            trace.summary['api_revision_dependencies'],
            [{
                'step_logical_id': f'step-{self.step.id}',
                'api_info_id': str(self.api_info.id),
                'api_info_revision_id': str(revision_v1.api_bindings.get().api_info_revision_id),
                'checksum': revision_v1.api_bindings.get().api_info_revision.checksum,
            }],
        )

    def test_runtime_test_case_accepts_release_id_without_revision_id(self):
        from src.apps.auto_api.services.execution.cases.test_case import TestCase as RuntimeTestCase

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        with patch(
                'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                return_value=15,
        ):
            runtime_case = RuntimeTestCase(
                user_id=self.owner.id,
                test_env=0,
                case_id=self.case.id,
                release_id=release.id,
            )

        self.assertEqual(runtime_case.api_case_result.case_revision_id, revision.id)
        self.assertEqual(runtime_case.api_case_result.case_release_id, release.id)
        self.assertEqual(runtime_case.api_case_result.version_label, release.version_label)

    def test_mcp_case_tree_contains_current_publication_state(self):
        from src.interfaces.mcp.tools.api.helper_parts.case_result import _case_tree

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        case_data = _case_tree(self.case.id, include_result_data=False)['case']

        self.assertEqual(case_data['published_revision_id'], revision.id)
        self.assertEqual(case_data['published_release_id'], release.id)
        self.assertEqual(case_data['published_version_label'], release.version_label)

    def test_runtime_rejects_frozen_checksum_mismatch(self):
        from src.apps.auto_api.services.execution.cases.test_case import TestCase as RuntimeTestCase

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        with patch(
                'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                return_value=15,
        ), self.assertRaises(AutoApiError):
            RuntimeTestCase(
                user_id=self.owner.id,
                test_env=0,
                case_id=self.case.id,
                revision_id=revision.id,
                config_checksum='invalid-checksum',
            )

    def test_api_request_uses_snapshot_api_without_reloading_current_row(self):
        from src.apps.auto_api.services.execution.base.api_base_test_setup import APIBaseTestSetup
        from src.apps.auto_api.schemas.execution import ApiExecutionRequest, ApiExecutionResponse

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        aggregate = ApiCaseRevisionService.load_execution_revision(revision.id)
        snapshot_api = aggregate.steps[0].api_info
        with patch(
                'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                return_value=15,
        ):
            setup = APIBaseTestSetup()
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='{}')
        request_model = ApiExecutionRequest(
            method='POST',
            url=f'http://example.test{snapshot_api.url}',
            protocol_type=snapshot_api.protocol_type,
            body_type=snapshot_api.body_type,
        )

        with patch.object(ApiInfo.objects, 'get') as current_api_get, \
                patch.object(setup, 'init_test_object'), \
                patch.object(setup, 'init_public'), \
                patch.object(setup, 'http', return_value=response):
            result = setup.api_request(
                snapshot_api.id,
                0,
                request_model,
                api_info=snapshot_api,
            )

        current_api_get.assert_not_called()
        self.assertEqual(result.code, 200)

    def test_revision_scenario_execution_uses_frozen_request_and_does_not_write_current_rows(self):
        from src.apps.auto_api.services.execution.cases.test_case import TestCase as RuntimeTestCase
        from mangotools.enums import StatusEnum
        from src.apps.auto_api.schemas.execution import ApiExecutionResponse

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])
        self.parameter.body_config = {'json': {'contract_name': 'v2-current'}}
        self.parameter.save(update_fields=['body_config', 'update_time'])
        with patch(
                'src.apps.auto_api.services.execution.base.api_base_test_setup.base_request.CacheDataValue.get_cache_value',
                return_value=15,
        ):
            runtime_case = RuntimeTestCase(
                user_id=self.owner.id,
                test_env=0,
                case_id=self.case.id,
                revision_id=revision.id,
            )
        step = runtime_case.get_case_detailed_queryset(self.case.id, None)[0]
        response = ApiExecutionResponse(code=200, time=0.1, headers={}, json={}, text='{}')

        with patch.object(runtime_case.test_setup, 'init_test_object'), \
                patch.object(runtime_case.test_setup, 'init_public'), \
                patch('src.apps.auto_api.services.execution.cases.test_case.GrayCaseExecutionRunner.apply_api_parameter',
                      return_value=[]), \
                patch('src.apps.auto_api.services.execution.cases.test_case.ParameterDataFactory.run_front'), \
                patch('src.apps.auto_api.services.execution.cases.test_case.ParameterDataFactory.cleanup'), \
                patch('src.apps.auto_api.services.execution.cases.test_case.CaseParameter.headers', return_value={}), \
                patch('src.apps.auto_api.services.execution.cases.test_case.CaseParameter.front_main',
                      side_effect=lambda request: request), \
                patch('src.apps.auto_api.services.execution.cases.test_case.CaseParameter.posterior_main',
                      return_value=response), \
                patch('src.apps.auto_api.services.execution.cases.test_case.CaseParameter.ass_main',
                      return_value=([], StatusEnum.SUCCESS.value, None)), \
                patch.object(runtime_case.test_setup, 'api_request', return_value=response) as api_request:
            execution_result = runtime_case.detailed_parameter(step)

        self.assertIsNone(execution_result)
        frozen_api = api_request.call_args.kwargs['api_info']
        frozen_request = api_request.call_args.args[2]
        self.assertEqual(frozen_api.url, '/open-apis/contracts')
        self.assertEqual(frozen_request.body_config, {'json': {'contract_name': '${contract_name}'}})
        self.parameter.refresh_from_db()
        self.api_info.refresh_from_db()
        self.assertEqual(self.parameter.result_data, {'response': {'id': 99}})
        self.assertEqual(self.api_info.url, '/open-apis/contracts/v2')

    def test_revision_and_prepublication_api_publish_current_snapshot(self):
        ExecutionResult.objects.create(
            source_type='page',
            target_type='api_case',
            target_id=self.case.id,
            status=StatusEnum.SUCCESS.value,
        )
        revision_response = self.client.post(
            '/api/api/case/revision',
            data=json.dumps({
                'case_id': self.case.id,
                'summary': '发布前快照',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )
        revision_body = revision_response.json()

        self.assertEqual(revision_body['code'], 200)
        self.assertEqual(revision_body['data']['revision_no'], 1)
        revision_id = revision_body['data']['id']

        submit_response = self.client.post(
            '/api/api/case/prepublication',
            data=json.dumps({
                'case_id': self.case.id,
                'revision_id': revision_id,
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )
        submit_body = submit_response.json()

        self.assertEqual(submit_body['code'], 200)
        self.assertEqual(submit_body['data']['prepublished_revision_id'], revision_id)

        release_response = self.client.post(
            '/api/api/case/prepublication/approve',
            data=json.dumps({'case_id': self.case.id}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )
        release_body = release_response.json()

        self.assertEqual(release_body['code'], 200)
        self.assertEqual(release_body['data']['version_label'], 'V1')
        self.assertTrue(release_body['data']['is_current'])
        self.assertFalse(
            ApiCaseRelease.objects.filter(
                revision_id=revision_id,
                status=ApiCaseReleaseStatusEnum.PREPUBLISHED.value,
            ).exists()
        )

        list_response = self.client.get(
            '/api/api/case/revision',
            {'case_id': self.case.id},
            HTTP_AUTHORIZATION=self.token,
        )
        list_body = list_response.json()
        self.assertEqual(list_body['code'], 200)
        self.assertEqual(list_body['data'][0]['id'], revision_id)
        self.assertEqual(list_body['data'][0]['release']['version_label'], 'V1')

        detail_response = self.client.get(
            '/api/api/case/revision/detail',
            {'id': revision_id},
            HTTP_AUTHORIZATION=self.token,
        )
        detail_body = detail_response.json()
        self.assertEqual(detail_body['code'], 200)
        self.assertEqual(detail_body['data']['payload']['steps'][0]['parameters'][0]['name'], '创建订单成功')

    def test_prepublication_demotes_current_release_and_approval_sets_only_new_current(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v1 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.case.name = '订单创建链路 V2'
        self.case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.case.id, source='test')

        ApiCaseRevisionService.submit_prepublication(self.case.id, revision_v2.id)

        state = ApiCaseRevisionService.get_publication_state(self.case.id)
        self.assertEqual(state.publication_status, ApiCaseRevisionService.PUBLICATION_PREPUBLISHED)
        self.assertEqual(state.prepublished_revision_id, revision_v2.id)
        self.assertIsNone(state.published_revision_id)
        release_v1.refresh_from_db()
        self.assertFalse(release_v1.is_current)
        self.assertEqual(release_v1.status, ApiCaseRelease.STATUS_PUBLISHED)
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.resolve_current_published(self.case.id)
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.resolve_release(self.case.id, release_v1.id)
        approved = ApiCaseRevisionService.approve_prepublication(self.case.id, operator_id=self.owner.id)
        self.assertTrue(approved.is_current)
        self.assertEqual(approved.replaced_release_id, release_v1.id)
        self.assertEqual(ApiCaseRelease.objects.filter(api_case=self.case, is_current=True).count(), 1)
        self.assertEqual(ApiCaseRevisionService.get_publication_state(self.case.id).publication_status, 'published')

    def test_reverting_prepublication_does_not_restore_historical_release(self):
        first = ApiCaseRevisionService.record_current(self.case.id, source='test')
        old = ApiCaseRevisionService._publish_revision(self.case.id, first.id, publisher_id=self.owner.id)
        self.case.name = 'New candidate'
        self.case.save(update_fields=['name'])
        candidate = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService.submit_prepublication(self.case.id, candidate.id)
        # 模拟旧流程留下的双状态，读取和退回都不能恢复旧正式版本。
        ApiCaseRelease.objects.filter(id=old.id).update(is_current=True)
        state = ApiCaseRevisionService.get_publication_state(self.case.id)
        self.assertEqual(state.publication_status, 'prepublished')
        self.assertIsNone(state.published_release_id)
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.resolve_current_published(self.case.id)
        response = self.client.get('/api/api/case/revision', {'case_id': self.case.id}, HTTP_AUTHORIZATION=self.token)
        self.assertEqual(response.json()['code'], 200)
        self.assertFalse(next(row for row in response.json()['data'] if row['id'] == first.id)['release']['is_current'])
        ApiCaseRevisionService.revert_prepublication(self.case.id, operator_id=self.owner.id)
        self.assertEqual(ApiCaseRevisionService.get_publication_state(self.case.id).publication_status, 'unpublished')
        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case, is_current=True).exists())

    def test_current_published_revision_cannot_be_submitted_again(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)

        self.assertEqual(context.exception.code, 31211)

    def test_internal_publish_is_idempotent_for_current_revision(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')

        first = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )
        second = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        self.assertEqual(second.id, first.id)
        self.assertEqual(
            ApiCaseRelease.objects.filter(api_case=self.case).count(),
            1,
        )

    def test_non_owner_can_revert_but_cannot_approve_prepublication(self):
        non_owner = User.objects.create(
            name='普通发布人员',
            username='case_version_publisher',
            password='pwd',
            is_super_admin=True,
        )
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)

        with self.assertRaises(AutoApiError) as approve_context:
            ApiCaseRevisionService.approve_prepublication(
                self.case.id,
                operator_id=non_owner.id,
            )
        self.assertEqual(approve_context.exception.code, 31208)

        returned = ApiCaseRevisionService.revert_prepublication(
            self.case.id,
            operator_id=non_owner.id,
        )
        self.assertEqual(returned.id, revision.id)
        self.assertTrue(ApiCaseRevision.objects.filter(id=revision.id).exists())
        self.assertFalse(ApiCaseRelease.objects.filter(revision=revision).exists())

    def test_owner_can_revert_prepublication_without_deleting_revision(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)

        ApiCaseRevisionService.revert_prepublication(
            self.case.id,
            operator_id=self.owner.id,
        )

        self.assertFalse(ApiCaseRelease.objects.filter(revision=revision).exists())

    def test_prepublication_requires_configured_product_owner(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        self.product.owners.clear()

        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)

        self.assertEqual(context.exception.code, 31207)

    def test_prepublished_revision_cannot_be_deleted(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService.submit_prepublication(self.case.id, revision.id)

        with self.assertRaises(AutoApiError) as context:
            ApiCaseRevisionService.delete_unpublished_revision(self.case.id, revision.id)

        self.assertEqual(context.exception.code, 31209)

    def test_release_api_can_unpublish_current_version(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        response = self.client.post(
            '/api/api/case/release/unpublish',
            data=json.dumps({
                'case_id': self.case.id,
                'release_id': release.id,
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        body = response.json()
        self.assertEqual(body['code'], 200)
        self.assertFalse(body['data']['is_current'])
        self.assertEqual(body['data']['status'], ApiCaseRelease.STATUS_DEPRECATED)

    def test_manual_execution_passes_selected_revision_to_runtime(self):
        from mangotools.enums import StatusEnum
        from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )
        result = ApiCaseExecutionResult(
            id=self.case.id,
            name=self.case.name,
            project_product_name=self.product.name,
            status=StatusEnum.SUCCESS.value,
            test_env=0,
            user_id=self.owner.id,
            case_revision_id=revision.id,
            case_revision_no=revision.revision_no,
            case_release_id=release.id,
            version_label=release.version_label,
            config_checksum=revision.checksum,
        )

        with patch('src.apps.auto_api.api.views.api_case.TestCase') as runtime_case:
            runtime_case.return_value.test_case.return_value = result
            response = self.client.get(
                '/api/api/case/test',
                {
                    'case_id': self.case.id,
                    'test_env': 0,
                    'revision_id': revision.id,
                    'release_id': release.id,
                },
                HTTP_AUTHORIZATION=self.token,
            )

        self.assertEqual(response.json()['code'], 200)
        runtime_case.assert_called_once_with(
            user_id=self.owner.id,
            test_env='0',
            case_id=str(self.case.id),
            revision_id=revision.id,
            release_id=release.id,
        )

    def test_manual_execution_without_selected_version_uses_current_published_release(self):
        from mangotools.enums import StatusEnum
        from src.apps.auto_api.schemas.execution import ApiCaseExecutionResult

        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v1 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.case.name = '尚未发布的当前草稿'
        self.case.save(update_fields=['name', 'update_time'])
        ApiCaseRevisionService.record_current(self.case.id, source='test')
        result = ApiCaseExecutionResult(
            id=self.case.id,
            name=revision_v1.payload['name'],
            project_product_name=self.product.name,
            status=StatusEnum.SUCCESS.value,
            test_env=0,
            user_id=self.owner.id,
            case_revision_id=revision_v1.id,
            case_revision_no=revision_v1.revision_no,
            case_release_id=release_v1.id,
            version_label=release_v1.version_label,
            config_checksum=revision_v1.checksum,
        )

        with patch('src.apps.auto_api.api.views.api_case.TestCase') as runtime_case:
            runtime_case.return_value.test_case.return_value = result
            response = self.client.get(
                '/api/api/case/test',
                {'case_id': self.case.id, 'test_env': 0},
                HTTP_AUTHORIZATION=self.token,
            )

        self.assertEqual(response.json()['code'], 200)
        runtime_case.assert_called_once_with(
            user_id=self.owner.id,
            test_env='0',
            case_id=str(self.case.id),
            revision_id=revision_v1.id,
            release_id=release_v1.id,
            config_checksum=revision_v1.checksum,
        )

    def test_batch_execution_pins_each_cases_current_published_revision(self):
        from src.apps.test_center.enums import TestCaseTypeEnum

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )
        self.case.name = '未发布草稿 V2'
        self.case.save(update_fields=['name', 'update_time'])
        ApiCaseRevisionService.record_current(self.case.id, source='test')

        with patch('src.apps.auto_api.services.api_case.batch_execution.AddTasks') as add_tasks:
            response = self.client.post(
                '/api/api/case/batch',
                data=json.dumps({
                    'case_id_list': [self.case.id],
                    'test_env': 0,
                    'execution_name': '发布版本批量执行',
                    'execution_version': 'published',
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=self.token,
            )

        response_body = response.json()
        self.assertEqual(response_body['code'], 200)
        self.assertEqual(response_body['data']['executions'], [{
            'case_id': self.case.id,
            'case_release_id': release.id,
            'case_revision_id': revision.id,
            'case_revision_no': revision.revision_no,
            'version_label': release.version_label,
            'execution_source': 'published',
            'config_checksum': revision.checksum,
        }])
        add_tasks.return_value.add_test_suite_details.assert_called_once_with(
            self.case.id,
            TestCaseTypeEnum.API,
            api_case_revision_id=revision.id,
            api_case_release_id=release.id,
            bound_checksum=revision.checksum,
        )

    def test_batch_execution_rejects_unpublished_case_in_published_mode(self):
        with patch('src.apps.auto_api.services.api_case.batch_execution.AddTasks') as add_tasks:
            response = self.client.post(
                '/api/api/case/batch',
                data=json.dumps({
                    'case_id_list': [self.case.id],
                    'test_env': 0,
                    'execution_name': '错误的发布版本批量执行',
                    'execution_version': 'published',
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=self.token,
            )

        body = response.json()
        self.assertNotEqual(body['code'], 200)
        self.assertIn(f'{self.case.id}-{self.case.name}', body['msg'])
        add_tasks.assert_not_called()

    def test_batch_execution_rejects_explicit_case_release_id(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release_v1 = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )

        with patch('src.apps.auto_api.services.api_case.batch_execution.AddTasks') as add_tasks:
            response = self.client.post(
                '/api/api/case/batch',
                data=json.dumps({
                    'case_items': [{
                        'case_id': self.case.id,
                        'case_release_id': release_v1.id,
                    }],
                    'test_env': 0,
                    'execution_name': '指定发布版本批量执行',
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=self.token,
            )

        self.assertNotEqual(response.json()['code'], 200)
        self.assertIn('execution_version', response.json()['msg'])
        add_tasks.assert_not_called()

    def test_batch_execution_rejects_other_execution_version(self):
        with patch('src.apps.auto_api.services.api_case.batch_execution.AddTasks') as add_tasks:
            response = self.client.post(
                '/api/api/case/batch',
                data=json.dumps({
                    'case_id_list': [self.case.id],
                    'test_env': 0,
                    'execution_name': '错误版本批量执行',
                    'execution_version': 'release',
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=self.token,
            )

        self.assertNotEqual(response.json()['code'], 200)
        self.assertIn('editing 或 published', response.json()['msg'])
        add_tasks.assert_not_called()

    def test_batch_execution_uses_current_editing_case_without_creating_revision(self):
        from src.apps.test_center.enums import TestCaseTypeEnum

        revision_count = ApiCaseRevision.objects.filter(api_case=self.case).count()
        with patch('src.apps.auto_api.services.api_case.batch_execution.AddTasks') as add_tasks:
            response = self.client.post(
                '/api/api/case/batch',
                data=json.dumps({
                    'case_id_list': [self.case.id],
                    'test_env': 0,
                    'execution_name': '未发布编辑态批量执行',
                }),
                content_type='application/json',
                HTTP_AUTHORIZATION=self.token,
            )

        response_body = response.json()
        self.assertEqual(response_body['code'], 200)
        execution = response_body['data']['executions'][0]
        self.assertEqual(execution['case_id'], self.case.id)
        self.assertIsNone(execution['case_revision_id'])
        self.assertIsNone(execution['case_release_id'])
        self.assertEqual(execution['execution_source'], 'editing')
        self.assertEqual(execution['version_label'], '当前编辑态')
        self.assertEqual(
            ApiCaseRevision.objects.filter(api_case=self.case).count(),
            revision_count,
        )
        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case).exists())
        add_tasks.return_value.add_test_suite_details.assert_called_once_with(
            self.case.id,
            TestCaseTypeEnum.API,
            api_case_revision_id=None,
            api_case_release_id=None,
            bound_checksum=None,
        )

    def test_case_list_exposes_publication_state_separately_from_run_status(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.case.status = 0
        self.case.save(update_fields=['status', 'update_time'])
        self.parameter.body_config = {'json': {'version': 2}}
        self.parameter.save(update_fields=['body_config', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.case.id, source='test')

        response = self.client.get(
            '/api/api/case',
            {'id': self.case.id, 'page': 1, 'pageSize': 20},
            HTTP_AUTHORIZATION=self.token,
        )
        body = response.json()
        row = body['data'][0]

        self.assertEqual(row['status'], 0)
        self.assertEqual(row['publication_status'], 'published')
        self.assertEqual(row['published_version_label'], 'V1')
        self.assertEqual(row['published_revision_id'], revision_v1.id)
        self.assertEqual(row['current_revision_id'], revision_v2.id)
        self.assertTrue(row['has_unpublished_changes'])

    def test_case_list_filters_publication_status_before_per_page_enrichment(self):
        revision_v1 = ApiCaseRevisionService.record_current(self.case.id, source='test')
        ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.parameter.body_config = {'json': {'version': 2}}
        self.parameter.save(update_fields=['body_config', 'update_time'])
        ApiCaseRevisionService.record_current(self.case.id, source='test')

        published_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='仅已发布用例',
            case_people=self.owner,
            status=1,
        )
        published_revision = ApiCaseRevisionService.record_current(published_case.id, source='test')
        ApiCaseRevisionService._publish_revision(
            published_case.id,
            published_revision.id,
            publisher_id=self.owner.id,
        )

        original_get_state = ApiCaseRevisionService.get_publication_state
        with patch.object(
                ApiCaseRevisionService,
                'get_publication_state',
                wraps=original_get_state,
        ) as get_state:
            response = self.client.get(
                '/api/api/case',
                {
                    'publication_status': 'published',
                    'page': 1,
                    'pageSize': 20,
                },
                HTTP_AUTHORIZATION=self.token,
            )

        body = response.json()
        self.assertEqual(body['code'], 200)
        self.assertEqual(body['totalSize'], 2)
        self.assertEqual({row['id'] for row in body['data']}, {self.case.id, published_case.id})
        self.assertTrue(all(row['publication_status'] == 'published' for row in body['data']))
        self.assertEqual(get_state.call_count, 2)

    def test_sensitive_values_allow_plaintext_and_runtime_reference_templates(self):
        allowed_payloads = (
            {'password': 123},
            {'password': 'raw-${secret_ref}'},
            {'password': {'secret_ref': '${vault_password}', 'value': 'raw'}},
            {'password': 'Bearer ${{password}}'},
            {'body': "{'password':'raw'}"},
            {'authorization': 'raw ${{token}}'},
            {'authorization': 'Bearer ${{token}} raw-token'},
        )

        for payload in allowed_payloads:
            with self.subTest(payload=payload):
                ApiExecutableSnapshotService.validate_sensitive_references(payload)

        ApiExecutableSnapshotService.validate_sensitive_references({
            'password': '${vault_password}',
            'headers': {'Authorization': 'Bearer ${{zs_token_test}}'},
            'header_items': [{'key': 'Authorization', 'value': 'Bearer ${{zs_token_test}}'}],
            'authorization': {'auth_config_id': 12},
        })

    def test_authorization_bearer_runtime_reference_can_be_published(self):
        authorization_header = ApiHeaders.objects.create(
            project_product=self.product,
            key='Authorization',
            value='Bearer ${{zs_token_test}}',
            status=1,
        )
        self.case.front_headers = [authorization_header.id]
        self.case.save(update_fields=['front_headers', 'update_time'])

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        self.assertEqual(
            revision.payload['resolved_front_headers']['Authorization'],
            'Bearer ${{zs_token_test}}',
        )
        self.assertEqual(release.revision_id, revision.id)

    def test_pagination_token_values_can_be_published_without_weakening_auth_token_checks(self):
        self.parameter.body_config = {
            'body': {
                'page_token': 'opaque-page-cursor',
                'nextPageToken': 'opaque-next-page-cursor',
            },
        }
        self.parameter.save(update_fields=['body_config', 'update_time'])

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        body = revision.payload['steps'][0]['parameters'][0]['body_config']['body']
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        self.assertEqual(body['page_token'], 'opaque-page-cursor')
        self.assertEqual(body['nextPageToken'], 'opaque-next-page-cursor')
        self.assertEqual(release.revision_id, revision.id)
        for sensitive_key in ('access_token', 'refreshToken', 'client_token'):
            with self.subTest(sensitive_key=sensitive_key):
                ApiExecutableSnapshotService.validate_sensitive_references({
                    sensitive_key: 'plaintext-auth-token',
                })

    def test_plaintext_secret_is_preserved_and_can_be_published(self):
        self.api_info.headers = {'Authorization': 'Bearer raw-secret'}
        self.api_info.save(update_fields=['headers', 'update_time'])

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        serialized = json.dumps(
            revision.api_bindings.get().api_info_revision.payload,
            ensure_ascii=False,
        )

        self.assertIn('raw-secret', serialized)
        self.assertNotIn('${secret_required:', serialized)
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )
        self.assertEqual(release.revision_id, revision.id)

    def test_publish_rejects_revision_without_executable_steps(self):
        empty_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='空用例',
            case_people=self.owner,
            case_flow='',
            status=1,
        )
        revision = ApiCaseRevisionService.record_current(empty_case.id, source='test')

        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService._publish_revision(
                empty_case.id,
                revision.id,
                publisher_id=self.owner.id,
            )

        self.assertFalse(ApiCaseRelease.objects.filter(api_case=empty_case).exists())

    def test_publish_rejects_step_without_scenarios(self):
        self.parameter.delete()
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')

        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService._publish_revision(
                self.case.id,
                revision.id,
                publisher_id=self.owner.id,
            )

        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case).exists())

    def test_publish_rejects_missing_shared_header_reference(self):
        self.case.front_headers = [999999]
        self.case.save(update_fields=['front_headers', 'update_time'])
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')

        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService._publish_revision(
                self.case.id,
                revision.id,
                publisher_id=self.owner.id,
            )

        self.assertEqual(revision.payload['missing_front_header_ids'], [999999])
        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case).exists())

    def test_execution_rejects_unsupported_snapshot_schema_version(self):
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        revision.snapshot_schema_version = 999
        revision.save(update_fields=['snapshot_schema_version'])

        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.load_execution_revision(revision.id)

    def test_publish_rejects_active_data_factory_until_template_revision_is_frozen(self):
        from src.apps.data_factory.models import (
            DataFactoryCaseConfig,
            DataFactoryEntity,
            DataFactoryTemplate,
        )
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum

        entity = DataFactoryEntity.objects.create(
            project_product=self.product,
            module=self.module,
            name='待冻结实体',
            table_name='contract',
        )
        template = DataFactoryTemplate.objects.create(
            project_product=self.product,
            module=self.module,
            entity=entity,
            name='待冻结模板',
        )
        DataFactoryCaseConfig.objects.create(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
            source_id=self.case.id,
            template=template,
            name='contract',
            status=1,
        )
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')

        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService._publish_revision(
                self.case.id,
                revision.id,
                publisher_id=self.owner.id,
            )

        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case).exists())

    def test_publish_rejects_active_gray_config_until_feature_revision_is_frozen(self):
        from src.apps.gray_config.enums import (
            GrayCaseScopeEnum,
            GrayCaseTypeEnum,
            GrayConfigTypeEnum,
        )
        from src.apps.gray_config.models import AutomationCaseGrayConfig, GrayFeature

        feature = GrayFeature.objects.create(
            gray_code='GRAY-CASE-VERSION',
            config_type=GrayConfigTypeEnum.CODE.value,
            project_product=self.product,
            module=self.module,
            name='待冻结灰度',
            feature_key='contract.version',
            enable_code='def gray(context):\n    return True',
        )
        AutomationCaseGrayConfig.objects.create(
            case_type=GrayCaseTypeEnum.API.value,
            scope=GrayCaseScopeEnum.CASE.value,
            api_case=self.case,
            gray_feature=feature,
            status=1,
        )
        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')

        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService._publish_revision(
                self.case.id,
                revision.id,
                publisher_id=self.owner.id,
            )

        self.assertFalse(ApiCaseRelease.objects.filter(api_case=self.case).exists())

    def test_historical_revision_gray_execution_never_queries_current_bindings(self):
        from src.apps.gray_config.models import AutomationCaseGrayConfig
        from src.apps.gray_config.services.execution_runner import GrayCaseExecutionRunner

        revision = ApiCaseRevisionService.record_current(self.case.id, source='test')
        aggregate = ApiCaseRevisionService.load_execution_revision(revision.id)
        frozen_step = aggregate.steps[0]
        frozen_parameter = aggregate.parameters_for_step(frozen_step)[0]

        with patch.object(
                AutomationCaseGrayConfig.objects,
                'select_related',
                side_effect=AssertionError('历史版本不应查询当前灰度绑定'),
        ):
            case_configs = GrayCaseExecutionRunner.apply_api_case(aggregate.api_case)
            parameter_configs = GrayCaseExecutionRunner.apply_api_parameter(
                aggregate.api_case,
                frozen_step,
                frozen_parameter,
            )

        self.assertEqual(case_configs, [])
        self.assertEqual(parameter_configs, [])

    def test_publish_permission_is_available_to_role_configuration(self):
        self.assertIn('publish', PermissionMenuService.ACTION_LABELS)
        self.assertIn('publish', PermissionMenuService.MENU_ACTIONS['api.case'])
        self.assertIn('api.case:change', PermissionMenuService.all_permission_keys())
