from django.test import SimpleTestCase

from src.apps.auto_api.enums import ApiProtocolTypeEnum
from src.apps.auto_api.schemas.execution import ApiCaseStepResult, ApiExecutionRequest, ApiExecutionResponse


class ResponseModelSerializationTests(SimpleTestCase):
    @staticmethod
    def build_response(**kwargs):
        data = {
            'code': 200,
            'time': 0.1,
            'headers': {},
            'json': None,
            'text': None,
        }
        data.update(kwargs)
        return ApiExecutionResponse(**data)

    def test_json_response_keeps_runtime_text_but_does_not_serialize_it(self):
        response = self.build_response(
            json={'code': 0},
            text='{"code":0}',
        )

        self.assertEqual(response.text, '{"code":0}')
        self.assertNotIn('text', response.model_dump())

    def test_text_response_serializes_text_when_json_is_unavailable(self):
        response = self.build_response(text='plain text')

        self.assertEqual(response.model_dump()['text'], 'plain text')

    def test_sse_response_keeps_full_text_even_when_last_event_has_json(self):
        response = self.build_response(
            response_mode=ApiProtocolTypeEnum.SSE.value,
            json={'done': True},
            text='event: message\ndata: {"done":true}',
        )

        self.assertEqual(
            response.model_dump()['text'],
            'event: message\ndata: {"done":true}',
        )

    def test_nested_case_result_also_omits_duplicate_json_text(self):
        step_result = ApiCaseStepResult(
            id=1,
            name='测试步骤',
            status=1,
            api_info_id=1,
            api_info_name='测试接口',
            request=ApiExecutionRequest(method='GET', url='https://example.test'),
            response=self.build_response(json={'code': 0}, text='{"code":0}'),
            cache_data={},
        )

        self.assertNotIn('text', step_result.model_dump()['response'])
