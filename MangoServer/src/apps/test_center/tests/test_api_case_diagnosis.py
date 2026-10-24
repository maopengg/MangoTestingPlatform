import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.test_center.services.api_case_diagnosis import ApiCaseDiagnosisService


class ApiCaseDiagnosisTests(SimpleTestCase):
    def make_result(self, status=0):
        return SimpleNamespace(
            id=42, target_id=7, test_env=0, revision_id=2, release_id=None,
            create_time=datetime(2026, 1, 1), status=status, error_message='第三步断言失败',
            result_cleaned=False, result_size=100, trace_id=None,
        )

    @patch.object(ApiCaseDiagnosisService, '_load')
    def test_no_failure_does_not_call_ai(self, load):
        load.return_value = {'steps': [{'id': 1, 'name': '通过步骤', 'status': 1}]}
        with patch('src.apps.test_center.services.api_case_diagnosis.AiService.json_chat') as chat:
            result = ApiCaseDiagnosisService.analyze(self.make_result(status=1))
        self.assertFalse(result['available'])
        chat.assert_not_called()

    @patch.object(ApiCaseDiagnosisService, '_load')
    @patch('src.apps.test_center.services.api_case_diagnosis.AiService._validate_base_config')
    @patch('src.apps.test_center.services.api_case_diagnosis.AiService.load_config')
    @patch('src.apps.test_center.services.api_case_diagnosis.AiService.json_chat')
    def test_long_flow_includes_focus_and_predecessor(self, chat, load_config, validate, load):
        load.return_value = {'steps': [
            {'id': index + 1, 'name': f'步骤{index + 1}', 'status': 0 if index == 8 else 1,
             'request': {'url': f'https://example.com/path/{index}', 'method': 'GET'},
             'response': {'code': 200, 'json': {'token': 'secret-token', 'value': index}}}
            for index in range(10)
        ]}
        chat.return_value = {'choices': [{'message': {'content': json.dumps({
            'cause': '第九步校验失败', 'evidence': ['断言未通过'], 'next_check': '检查数据',
            'confidence': 'medium',
        })}}]}
        result = ApiCaseDiagnosisService.analyze(self.make_result(), scope='auto')
        self.assertTrue(result['available'])
        evidence = json.loads(chat.call_args.kwargs['messages'][1]['content'])['evidence']
        self.assertEqual([step['unit_index'] for step in evidence['details']], [7, 8])
        self.assertNotIn('secret-token', chat.call_args.kwargs['messages'][1]['content'])
        self.assertEqual(result['included_unit_count'], 2)
        load_config.assert_called_once()
        validate.assert_called_once()
