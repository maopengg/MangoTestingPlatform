from unittest.mock import AsyncMock, Mock

from django.test import SimpleTestCase
from mangotools.enums import ActuatorPytestEventEnum

from src.apps.system.enums import ClientTypeEnum
from src.processes.realtime.consumer import RealtimeConsumer


class RealtimePytestCallbackTests(SimpleTestCase):
    async def test_pytest_page_and_report_results_are_persisted_before_browser_relay(self):
        for event in (ActuatorPytestEventEnum.TEST_CASE, ActuatorPytestEventEnum.TEST_CASE_BATCH):
            for result_code in (200, 300):
                with self.subTest(event=event, result_code=result_code):
                    consumer = RealtimeConsumer(registry=Mock(touch=AsyncMock()), service_instance='test')
                    consumer.connection_id = 'example-connection'
                    consumer.reflection = Mock()
                    consumer._relay = AsyncMock()
                    payload = {'code': result_code, 'msg': 'result', 'is_notice': ClientTypeEnum.WEB.value,
                               'user': 'example-user', 'message_id': 'example-message',
                               'data': {'func_name': event.value, 'func_args': {'id': 1}}}
                    await consumer.receive_json(payload)
                    consumer.reflection.server_data_received.send.assert_called_once()
                    forwarded = consumer.reflection.server_data_received.send.call_args.kwargs['data']
                    self.assertEqual(forwarded.func_name, event.value)
                    self.assertEqual(forwarded.message_id, 'example-message')
                    consumer._relay.assert_awaited_once()
