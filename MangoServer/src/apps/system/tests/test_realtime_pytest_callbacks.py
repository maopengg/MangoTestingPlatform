from unittest.mock import AsyncMock, Mock

from django.test import SimpleTestCase
from mangotools.enums import ActuatorPytestEventEnum

from src.apps.system.enums import ClientTypeEnum
from src.processes.realtime.consumer import RealtimeConsumer


class RealtimePytestCallbackTests(SimpleTestCase):
    async def test_browser_cannot_forge_executor_callbacks_or_relay_commands(self):
        consumer = RealtimeConsumer(registry=Mock(touch=AsyncMock()), service_instance='test')
        consumer.connection_id = 'example-connection'
        consumer.client_type = ClientTypeEnum.WEB.value
        consumer.reflection = Mock()
        consumer.send_json = AsyncMock()
        consumer._relay = AsyncMock()
        await consumer.receive_json({'code': 200, 'msg': '', 'data': {
            'func_name': ActuatorPytestEventEnum.TEST_CASE.value, 'func_args': {'id': 1},
        }})
        self.assertEqual(consumer.send_json.call_args.args[0]['code'], 403)
        consumer.reflection.server_data_received.send.assert_not_called()
        consumer._relay.assert_not_awaited()

    async def test_pytest_page_and_report_results_are_persisted_before_browser_relay(self):
        for event in (ActuatorPytestEventEnum.TEST_CASE, ActuatorPytestEventEnum.TEST_CASE_BATCH):
            for result_code in (200, 300):
                with self.subTest(event=event, result_code=result_code):
                    consumer = RealtimeConsumer(registry=Mock(touch=AsyncMock()), service_instance='test')
                    consumer.connection_id = 'example-connection'
                    consumer.client_type = ClientTypeEnum.ACTUATOR.value
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
