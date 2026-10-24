from django.test import TestCase

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiInfo,
    ApiInfoHttpConfig,
)
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.user.models import User


class ApiCaseSelfContainedRevisionTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='自包含快照测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='开放平台')
        self.module = ProductModule.objects.create(
            project_product=self.product,
            name='接口模块',
        )
        self.owner = User.objects.create(
            name='版本负责人',
            username='case_snapshot_owner',
            password='pwd',
            is_super_admin=True,
        )
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            update_user=self.owner,
            name='获取令牌',
            url='/open-apis/token',
            protocol_type='http',
            status=1,
        )
        ApiInfoHttpConfig.objects.create(
            api_info=self.api_info,
            method=2,
            url='/open-apis/token',
            headers={'Content-Type': 'application/json'},
            params=None,
            is_text_params=1,
            body_type='json',
            body_config={
                'source_type': 'value',
                'body': {'app_id': '${{app_id}}', 'app_secret': '${{app_secret}}'},
            },
            sse_config=None,
        )
        self.api_revision = ApiInfoRevisionService.record_current(
            self.api_info.id,
            operator_id=self.owner.id,
            source='test',
        )
        ApiInfoRevisionService.publish(
            self.api_info.id,
            self.api_revision.id,
            publisher_id=self.owner.id,
        )
        self.case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='令牌登录',
            case_people=self.owner,
            case_flow='1',
            status=1,
        )
        self.step = ApiCaseDetailed.objects.create(
            case=self.case,
            api_info=self.api_info,
            pinned_api_info_revision=self.api_revision,
            case_sort=1,
            status=1,
        )
        self.parameter = ApiCaseDetailedParameter.objects.create(
            case_detailed=self.step,
            update_user=self.owner,
            name='登录成功',
            headers=[],
            body_config=None,
            ass_jsonpath=[{
                'actual': '$.code',
                'expect': '0',
                'method': 'p_is_equal_to',
            }],
            status=1,
        )

    def test_revision_and_release_allow_scenario_without_assertion(self):
        self.parameter.ass_jsonpath = []
        self.parameter.save(update_fields=['ass_jsonpath', 'update_time'])

        revision = ApiCaseRevisionService.record_current(
            self.case.id,
            operator_id=self.owner.id,
            source='test',
        )
        release = ApiCaseRevisionService._publish_revision(
            self.case.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        self.assertEqual(release.revision_id, revision.id)

    def create_revision_and_remove_live_dependency(self):
        self.original_api_info_id = self.api_info.id
        self.original_api_revision_id = self.api_revision.id
        revision = ApiCaseRevisionService.record_current(
            self.case.id,
            operator_id=self.owner.id,
            source='test',
        )
        self.assertEqual(
            revision.payload['api_case_detailed'][0]['api_info_snapshot']['name'],
            '获取令牌',
        )
        self.step.delete()
        self.api_info.delete()
        return revision

    def test_execution_uses_embedded_api_snapshot_after_live_api_deleted(self):
        revision = self.create_revision_and_remove_live_dependency()

        aggregate = ApiCaseRevisionService.load_execution_revision(revision.id)

        self.assertEqual(aggregate.steps[0].api_info.name, '获取令牌')
        self.assertEqual(aggregate.steps[0].api_info.url, '/open-apis/token')
        self.assertEqual(
            aggregate.steps[0].api_info.body_config['body']['app_secret'],
            '${{app_secret}}',
        )

    def test_checkout_can_restore_deleted_dependency_with_new_ids(self):
        revision = self.create_revision_and_remove_live_dependency()
        impact = ApiCaseRevisionService.inspect_checkout_impact(self.case.id, revision.id)

        self.assertTrue(impact['can_checkout'])
        self.assertTrue(impact['requires_restore'])
        self.assertEqual(impact['items'][0]['status'], 'restorable')
        with self.assertRaises(AutoApiError):
            ApiCaseRevisionService.checkout_to_editing(
                self.case.id,
                revision.id,
                operator_id=self.owner.id,
            )

        ApiCaseRevisionService.checkout_to_editing(
            self.case.id,
            revision.id,
            operator_id=self.owner.id,
            restore_missing_dependencies=True,
        )

        restored_step = ApiCaseDetailed.objects.select_related(
            'api_info',
            'pinned_api_info_revision',
        ).get(case_id=self.case.id)
        self.assertNotEqual(restored_step.api_info_id, self.original_api_info_id)
        self.assertNotEqual(
            restored_step.pinned_api_info_revision_id,
            self.original_api_revision_id,
        )
        self.assertEqual(restored_step.api_info.name, '获取令牌（历史恢复）')
        self.assertEqual(restored_step.api_info.http_config.body_type, 'json')

    def test_legacy_case_snapshot_blocks_api_deletion(self):
        revision = ApiCaseRevisionService.record_current(
            self.case.id,
            operator_id=self.owner.id,
            source='test',
        )
        payload = revision.payload
        payload['api_case_detailed'][0].pop('api_info_snapshot', None)
        revision.payload = payload
        revision.checksum = ApiCaseRevisionService.checksum(payload)
        revision.save(update_fields=['payload', 'checksum'])
        self.step.delete()

        impact = ApiCaseRevisionService.inspect_api_info_delete_dependencies(self.api_info.id)

        self.assertFalse(impact['can_delete'])
        self.assertEqual(len(impact['legacy_history_references']), 1)
        with self.assertRaises(AutoApiError):
            self.api_info.delete()
