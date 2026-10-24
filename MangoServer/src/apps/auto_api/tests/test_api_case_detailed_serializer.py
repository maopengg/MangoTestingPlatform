from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_case_detailed import ApiCaseDetailedSerializersC


class ApiCaseDetailedSerializerTests(SimpleTestCase):

    @patch('src.apps.auto_api.api.serializers.api_case_detailed.ApiInfoSerializers')
    def test_api_info_uses_pinned_revision_runtime_request_type(self, serializer):
        serializer.return_value.data = {'id': 12, 'name': '上传附件'}
        step = SimpleNamespace(
            api_info=SimpleNamespace(),
            pinned_api_info_revision_id=34,
            pinned_api_info_revision=SimpleNamespace(payload={
                'api_info': {
                    'method': 1,
                    'url': '/resources',
                    'protocol_type': 'http',
                    'body_type': 'multipart',
                },
            }),
        )

        data = ApiCaseDetailedSerializersC.get_api_info(step)

        self.assertEqual(data['body_type'], 'multipart')
        self.assertEqual(data['protocol_type'], 'http')
        self.assertEqual(data['method'], 1)
        self.assertEqual(data['url'], '/resources')

    @patch('src.apps.auto_api.api.serializers.api_case_detailed.ApiInfoRuntimeService.current_payload')
    @patch('src.apps.auto_api.api.serializers.api_case_detailed.ApiInfoSerializers')
    def test_api_info_uses_current_runtime_request_type_for_legacy_step(
            self,
            serializer,
            current_payload,
    ):
        serializer.return_value.data = {'id': 12, 'name': '上传附件'}
        current_payload.return_value = {
            'method': 1,
            'url': '/resources',
            'protocol_type': 'http',
            'body_type': 'multipart',
        }
        step = SimpleNamespace(
            api_info=SimpleNamespace(),
            pinned_api_info_revision_id=None,
        )

        data = ApiCaseDetailedSerializersC.get_api_info(step)

        self.assertEqual(data['body_type'], 'multipart')
        current_payload.assert_called_once_with(step.api_info)
