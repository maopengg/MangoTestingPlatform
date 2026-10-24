import json
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.ai.exceptions import ai_service_error
from src.apps.test_center.services.assertion_diagnosis import AssertionDiagnosisService


class AssertionDiagnosisTests(SimpleTestCase):
    @patch('src.apps.test_center.services.assertion_diagnosis.AiService.json_chat')
    def test_passed_assertions_do_not_call_ai(self, chat):
        result = AssertionDiagnosisService.analyze([{'status': 1, 'actual': 'ok'}])
        self.assertFalse(result['available'])
        chat.assert_not_called()

    @patch('src.apps.test_center.services.assertion_diagnosis.AiService.load_config',
           side_effect=ai_service_error('未配置'))
    @patch('src.apps.test_center.services.assertion_diagnosis.AiService.json_chat')
    def test_missing_ai_configuration_returns_hint_without_call(self, chat, load_config):
        result = AssertionDiagnosisService.analyze([{'status': 0, 'actual': False, 'expect': True}])
        self.assertFalse(result['available'])
        self.assertIn('配置', result['reason'])
        chat.assert_not_called()
        load_config.assert_called_once()

    @patch('src.apps.test_center.services.assertion_diagnosis.AiService._validate_base_config')
    @patch('src.apps.test_center.services.assertion_diagnosis.AiService.load_config')
    @patch('src.apps.test_center.services.assertion_diagnosis.AiService.json_chat')
    def test_failure_calls_ai_once_and_masks_credentials(self, chat, load_config, validate):
        chat.return_value = {'choices': [{'message': {'content': json.dumps({
            'summary': '实际值与预期值不一致',
            'items': [
                {'assertion_index': 0, 'explanation': '实际值为 false，预期为 true', 'next_check': '检查响应字段'}],
        })}}]}
        result = AssertionDiagnosisService.analyze([
            {'status': 0, 'method': 'JSON一致', 'actual': {'token': 'sensitive', 'enabled': False},
             'expect': {'enabled': True}},
        ])
        self.assertTrue(result['available'])
        self.assertEqual(result['analyzed_count'], 1)
        self.assertEqual(result['items'][0]['assertion_index'], 0)
        self.assertEqual(result['items'][0]['explanation'], '实际值为 false，预期为 true')
        chat.assert_called_once()
        messages = chat.call_args.kwargs['messages']
        self.assertNotIn('sensitive', messages[1]['content'])
        load_config.assert_called_once()
        validate.assert_called_once()

    def test_message_masks_inline_bearer(self):
        value = AssertionDiagnosisService._safe_value('Authorization: Bearer abc.def.ghi')
        self.assertNotIn('abc.def.ghi', value)
