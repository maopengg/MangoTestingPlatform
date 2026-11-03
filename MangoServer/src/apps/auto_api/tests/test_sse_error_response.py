import time
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase

from src.apps.auto_api.schemas.execution import ApiExecutionRequest
from src.apps.auto_api.enums.assertion import ApiDefaultAssertionCheck
from src.apps.auto_api.services.base.api_base_test_setup.request_body import prepare_json_body
from src.apps.auto_api.services.protocols.http_sse import HttpSseProtocolClient
from src.apps.auto_api.services.protocols.outcome import ProtocolCallOutcomeService
from src.common.testing import ObtainTestData


class SseErrorResponseTests(SimpleTestCase):
    def test_rejected_stream_keeps_server_error_body(self):
        client_type = httpx.Client
        transport = httpx.MockTransport(lambda request: httpx.Response(
            400, json={'message': 'Missing renderer capability'}, request=request,
        ))
        with patch('src.apps.auto_api.services.protocols.http_sse.httpx.Client',
                   side_effect=lambda **kwargs: client_type(transport=transport, **kwargs)):
            cache = ObtainTestData()
            request = ApiExecutionRequest(method='POST', url='https://example.com/chat', protocol_type='sse', body_type='json')
            body = prepare_json_body({'body': {'message': 'question'}}, cache, 'json')
            result = HttpSseProtocolClient(test_data=cache, timeout=10).request(request, body, time.time())
        self.assertEqual(result.code, 400)
        self.assertEqual(result.json, {'message': 'Missing renderer capability'})
        self.assertEqual(result.request_protocol_type, 'sse')
        outcome = ProtocolCallOutcomeService.evaluate(result, default_checks=frozenset({ApiDefaultAssertionCheck.HTTP_STATUS}))
        self.assertFalse(outcome.success)
        self.assertIn('Missing renderer capability', outcome.error_message)
        self.assertTrue(ProtocolCallOutcomeService.evaluate(result, default_checks=frozenset()).success)
