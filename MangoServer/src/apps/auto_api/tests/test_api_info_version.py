from src.apps.user.services.http_permission_registry import permission_for_view
import json
from types import SimpleNamespace
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.api.views.api_info_version import ApiInfoRevisionViews
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiInfo, ApiInfoRelease, ApiInfoRevision
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.apps.test_center.models import ExecutionResult, ProductModule, Project, ProjectProduct
from src.apps.user.models import (
    Department,
    DepartmentProjectProductPermission,
    User,
    UserDepartment,
)
from src.apps.user.services.permission import AuthUserContext


class ApiInfoRevisionServiceTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='接口版本项目')
        self.product = ProjectProduct.objects.create(project=project, name='开放平台')
        self.module = ProductModule.objects.create(project_product=self.product, name='订单模块')
        self.owner = User.objects.create(
            name='接口负责人',
            username='api_version_owner',
            password='pwd',
            is_super_admin=True,
        )
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='创建订单',
            url='/open-apis/contracts',
            method=1,
            headers={'X-Trace': '${trace_id}'},
            params={'tenantId': '${tenant_id}'},
            body_config={'json': {'name': '${contract_name}'}},
            status=1,
        )
        self.token = jwt.encode({'id': self.owner.id}, settings.SECRET_KEY, algorithm='HS256')

    def test_publish_keeps_v1_current_while_v2_is_only_a_draft(self):
        revision_v1 = ApiInfoRevisionService.record_current(
            self.api_info.id,
            operator_id=self.owner.id,
            source='test',
        )
        release_v1 = ApiInfoRevisionService.publish(
            self.api_info.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])
        revision_v2 = ApiInfoRevisionService.record_current(self.api_info.id, source='test')

        state = ApiInfoRevisionService.get_publication_state(self.api_info.id)

        self.assertEqual(release_v1.version_label, 'V1')
        self.assertEqual(state.publication_status, 'draft_changed')
        self.assertEqual(state.published_revision_id, revision_v1.id)
        self.assertEqual(state.current_revision_id, revision_v2.id)
        self.assertTrue(state.has_unpublished_changes)

    def test_model_crud_update_only_changes_current_editing_state(self):
        from src.apps.auto_api.api.views.api_info import ApiInfoCRUD

        ApiInfoCRUD.inside_put(
            self.api_info.id,
            {'id': self.api_info.id, 'url': '/open-apis/contracts/v2'},
        )

        self.api_info.refresh_from_db()
        self.assertEqual(self.api_info.url, '/open-apis/contracts/v2')
        self.assertFalse(ApiInfoRevision.objects.filter(api_info=self.api_info).exists())

    def test_model_crud_update_does_not_call_revision_creation(self):
        from src.apps.auto_api.api.views.api_info import ApiInfoCRUD

        with patch.object(
                ApiInfoRevisionService,
                'record_current',
                side_effect=RuntimeError('revision failed'),
        ) as record_current:
            ApiInfoCRUD.inside_put(
                self.api_info.id,
                {'id': self.api_info.id, 'url': '/open-apis/contracts/v2'},
            )

        self.api_info.refresh_from_db()
        self.assertEqual(self.api_info.url, '/open-apis/contracts/v2')
        record_current.assert_not_called()
        self.assertFalse(ApiInfoRevision.objects.filter(api_info=self.api_info).exists())

    def test_revision_requires_latest_current_editing_run_to_succeed(self):
        with self.assertRaises(AutoApiError):
            ApiInfoRevisionService.ensure_current_editing_run_succeeded(self.api_info.id)

        ExecutionResult.objects.create(
            source_type='page',
            target_type='api_info',
            target_id=self.api_info.id,
            status=StatusEnum.FAIL.value,
        )
        with self.assertRaises(AutoApiError):
            ApiInfoRevisionService.ensure_current_editing_run_succeeded(self.api_info.id)

        ExecutionResult.objects.create(
            source_type='page',
            target_type='api_info',
            target_id=self.api_info.id,
            status=StatusEnum.SUCCESS.value,
        )
        ApiInfoRevisionService.ensure_current_editing_run_succeeded(self.api_info.id)

        self.api_info.name = '创建订单 V2'
        self.api_info.save(update_fields=['name', 'update_time'])
        with self.assertRaises(AutoApiError):
            ApiInfoRevisionService.ensure_current_editing_run_succeeded(self.api_info.id)

    def test_plaintext_secret_is_preserved_and_revision_can_be_published(self):
        self.api_info.headers = {'Authorization': 'Bearer plaintext-token'}
        self.api_info.save(update_fields=['headers', 'update_time'])

        revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        release = ApiInfoRevisionService.publish(
            self.api_info.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        self.assertEqual(
            revision.payload['headers']['Authorization'],
            'Bearer plaintext-token',
        )
        self.assertEqual(release.revision_id, revision.id)

    def test_authorization_runtime_reference_template_can_be_published(self):
        self.api_info.headers = {'Authorization': 'Bearer ${{zs_token_test}}'}
        self.api_info.save(update_fields=['headers', 'update_time'])

        revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        release = ApiInfoRevisionService.publish(
            self.api_info.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        self.assertEqual(
            revision.payload['headers']['Authorization'],
            'Bearer ${{zs_token_test}}',
        )
        self.assertEqual(release.revision_id, revision.id)

    def test_publish_rejects_unsupported_snapshot_schema_version(self):
        revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        revision.snapshot_schema_version = 999
        revision.save(update_fields=['snapshot_schema_version'])

        with self.assertRaises(AutoApiError):
            ApiInfoRevisionService.publish(
                self.api_info.id,
                revision.id,
                publisher_id=self.owner.id,
            )

    def test_restore_history_only_replaces_current_editing_config(self):
        revision_v1 = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.body_config = {'json': {'name': '${contract_name}', 'version': 2}}
        self.api_info.save(update_fields=['url', 'body_config', 'update_time'])
        revision_v2 = ApiInfoRevisionService.record_current(self.api_info.id, source='test')

        restored = ApiInfoRevisionService.restore(
            self.api_info.id,
            revision_v1.id,
            operator_id=self.owner.id,
            summary='回退错误契约',
        )

        self.api_info.refresh_from_db()
        revision_v1.refresh_from_db()
        revision_v2.refresh_from_db()
        self.assertEqual(restored.id, revision_v1.id)
        self.assertEqual(ApiInfoRevision.objects.filter(api_info=self.api_info).count(), 2)
        self.assertEqual(self.api_info.url, '/open-apis/contracts')
        self.assertEqual(self.api_info.body_config, {'json': {'name': '${contract_name}'}})
        self.assertEqual(revision_v1.payload['url'], '/open-apis/contracts')
        self.assertEqual(revision_v2.payload['url'], '/open-apis/contracts/v2')

    def test_revision_release_and_restore_endpoints(self):
        ExecutionResult.objects.create(
            source_type='page',
            target_type='api_info',
            target_id=self.api_info.id,
            status=StatusEnum.SUCCESS.value,
        )
        revision_response = self.client.post(
            '/api/api/info/revision',
            data=json.dumps({'api_info_id': self.api_info.id, 'summary': '接口初版'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )
        revision_body = revision_response.json()
        self.assertEqual(revision_body['code'], 200)
        revision_id = revision_body['data']['id']

        publish_response = self.client.post(
            '/api/api/info/release',
            data=json.dumps({
                'api_info_id': self.api_info.id,
                'revision_id': revision_id,
                'release_note': '稳定契约',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )
        self.assertEqual(publish_response.json()['data']['version_label'], 'V1')

        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])
        ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        restore_response = self.client.post(
            '/api/api/info/revision/restore',
            data=json.dumps({
                'api_info_id': self.api_info.id,
                'revision_id': revision_id,
                'summary': '恢复 V1',
            }),
            content_type='application/json',
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(restore_response.json()['code'], 200)
        self.assertEqual(restore_response.json()['data']['restored_from_revision'], revision_id)
        self.api_info.refresh_from_db()
        self.assertEqual(self.api_info.url, '/open-apis/contracts')
        self.assertEqual(ApiInfoRelease.objects.filter(api_info=self.api_info).count(), 1)

    def test_api_info_list_returns_publication_state(self):
        revision_v1 = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        release_v1 = ApiInfoRevisionService.publish(
            self.api_info.id,
            revision_v1.id,
            publisher_id=self.owner.id,
        )
        self.api_info.url = '/open-apis/contracts/v2'
        self.api_info.save(update_fields=['url', 'update_time'])
        revision_v2 = ApiInfoRevisionService.record_current(self.api_info.id, source='test')

        response = self.client.get(
            '/api/api/info',
            {'id': self.api_info.id, 'page': 1, 'pageSize': 10},
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.status_code, 200)
        row = response.json()['data'][0]
        self.assertEqual(row['current_revision_id'], revision_v2.id)
        self.assertEqual(row['current_revision_no'], revision_v2.revision_no)
        self.assertEqual(row['published_release_id'], release_v1.id)
        self.assertEqual(row['published_revision_id'], revision_v1.id)
        self.assertEqual(row['published_version_label'], 'V1')
        self.assertEqual(row['publication_status'], 'draft_changed')
        self.assertTrue(row['has_unpublished_changes'])

    def test_api_info_id_filter_returns_published_state(self):
        revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        release = ApiInfoRevisionService.publish(
            self.api_info.id,
            revision.id,
            publisher_id=self.owner.id,
        )

        response = self.client.get(
            '/api/api/info',
            {'id': self.api_info.id, 'page': 1, 'pageSize': 10},
            HTTP_AUTHORIZATION=self.token,
        )

        self.assertEqual(response.status_code, 200)
        row = response.json()['data'][0]
        self.assertEqual(row['published_release_id'], release.id)
        self.assertEqual(row['published_revision_id'], revision.id)
        self.assertEqual(row['publication_status'], 'published')
        self.assertFalse(row['has_unpublished_changes'])

    def test_restore_requires_publish_permission_and_target_revision_scope(self):
        revision_product_a = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        other_project = Project.objects.create(name='迁移后项目')
        other_product = ProjectProduct.objects.create(project=other_project, name='迁移后产品')
        other_module = ProductModule.objects.create(project_product=other_product, name='迁移后模块')
        self.api_info.project_product = other_product
        self.api_info.module = other_module
        self.api_info.save(update_fields=['project_product', 'module', 'update_time'])
        ApiInfoRevisionService.record_current(self.api_info.id, source='test')

        scoped_user = User.objects.create(
            name='仅迁移后产品用户',
            username='only_new_product',
            password='pwd',
        )
        department = Department.objects.create(name='迁移后产品部门')
        UserDepartment.objects.create(user=scoped_user, department=department)
        DepartmentProjectProductPermission.objects.create(
            department=department,
            project_product=other_product,
        )
        request = SimpleNamespace(user=AuthUserContext(scoped_user))

        self.assertEqual(
            permission_for_view(ApiInfoRevisionViews, 'restore'),
            'api.info:change',
        )
        self.assertTrue(ApiInfoRevisionViews.has_info_scope(request, self.api_info.id))
        self.assertFalse(
            ApiInfoRevisionViews.has_revision_scope(request, revision_product_a)
        )
