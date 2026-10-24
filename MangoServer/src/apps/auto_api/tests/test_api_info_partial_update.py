import json
from unittest.mock import patch

from django.test import TestCase

from src.apps.auto_api.api.views.api_info import ApiInfoCRUD
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiInfo, ApiInfoHttpConfig
from src.apps.auto_api.services.api_info.mutation import ApiInfoMutationService
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.apps.test_center.models import ProductModule, Project, ProjectProduct


class ApiInfoPartialUpdateTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='接口部分保存项目')
        product = ProjectProduct.objects.create(project=project, name='开放平台')
        module = ProductModule.objects.create(project_product=product, name='接口模块')
        self.api_info = ApiInfo.objects.create(
            project_product=product,
            module=module,
            name='部分保存接口',
            url='/open-apis/partial-update',
            protocol_type='http',
            status=1,
        )
        self.http_config = ApiInfoHttpConfig.objects.create(
            api_info=self.api_info,
            method=1,
            url='/open-apis/partial-update',
            headers={'X-Original': 'header'},
            params=None,
            is_text_params=1,
            body_type='json',
            body_config={'source_type': 'value', 'body': {'original': True}},
            sse_config=None,
        )

    def test_updating_headers_preserves_request_body(self):
        ApiInfoCRUD.inside_put(
            self.api_info.id,
            {'id': self.api_info.id, 'headers': {}},
            record_config=False,
        )

        self.http_config.refresh_from_db()
        self.assertEqual(self.http_config.headers, {})
        self.assertEqual(self.http_config.body_type, 'json')
        self.assertEqual(
            self.http_config.body_config,
            {'source_type': 'value', 'body': {'original': True}},
        )

    def test_updating_request_body_preserves_headers(self):
        ApiInfoCRUD.inside_put(
            self.api_info.id,
            {
                'id': self.api_info.id,
                'body_type': 'raw',
                'body_config': {
                    'content_type': 'text/plain',
                    'body_text': 'updated body',
                },
            },
            record_config=False,
        )

        self.http_config.refresh_from_db()
        self.assertEqual(self.http_config.headers, {'X-Original': 'header'})
        self.assertEqual(self.http_config.body_type, 'raw')
        self.assertEqual(
            self.http_config.body_config,
            {
                'content_type': 'text/plain',
                'body_text': 'updated body',
            },
        )

    def test_update_definition_persists_none_to_json_body(self):
        type(self.http_config).objects.filter(id=self.http_config.id).update(
            body_type='none',
            body_config={'source_type': 'template', 'body_text': '{}'},
        )

        ApiInfoMutationService.update_definition(
            self.api_info.id,
            {
                'body_type': 'json',
                'body_config': {'source_type': 'template', 'body_text': '{}'},
            },
            record_config=False,
        )

        self.http_config.refresh_from_db()
        self.assertEqual(self.http_config.body_type, 'json')
        self.assertEqual(
            self.http_config.body_config,
            {'source_type': 'template', 'body_text': '{}'},
        )

    def test_update_definition_persists_params_from_null(self):
        params = json.dumps(
            [{'key': 'pageIndex', 'value': 0}, {'key': 'pageSize', 'value': 10}],
            ensure_ascii=False,
        )

        ApiInfoMutationService.update_definition(
            self.api_info.id,
            {'params': params},
            record_config=False,
        )

        runtime = ApiInfoRuntimeService.resolve_runtime(self.api_info.id, allow_draft=True)
        self.assertEqual(runtime.params, params)

    def test_update_definition_rolls_back_when_readback_does_not_match(self):
        original_name = self.api_info.name

        with patch.object(ApiInfoRuntimeService, 'sync_protocol_config'):
            with self.assertRaises(AutoApiError):
                ApiInfoMutationService.update_definition(
                    self.api_info.id,
                    {'name': '不应落盘的名称', 'body_type': 'raw'},
                    record_config=False,
                )

        self.api_info.refresh_from_db()
        self.http_config.refresh_from_db()
        self.assertEqual(self.api_info.name, original_name)
        self.assertEqual(self.http_config.body_type, 'json')

    def test_revision_captures_updated_http_request_config(self):
        params = json.dumps([{'key': 'pageIndex', 'value': 0}], ensure_ascii=False)
        body_config = {'source_type': 'template', 'body_text': '{}'}
        ApiInfoMutationService.update_definition(
            self.api_info.id,
            {
                'params': params,
                'body_type': 'json',
                'body_config': body_config,
            },
            record_config=False,
        )

        revision = ApiInfoRevisionService.record_current(self.api_info.id)
        revision_config = revision.payload['api_info']

        self.assertEqual(revision_config['params'], params)
        self.assertEqual(revision_config['body_type'], 'json')
        self.assertEqual(revision_config['body_config'], body_config)
        self.assertEqual(revision_config['protocol_config']['config']['body_type'], 'json')
