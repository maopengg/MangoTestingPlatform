from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from django.db import OperationalError
from django.test import SimpleTestCase

from src.apps.system.api.views.socket_api import SocketApiViews
from src.apps.system.constants import RUNTIME_KV_POLICIES
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.actuator.actuator_config_runtime import ActuatorConfigRuntimeService
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.consumer.system import SystemConsumer


class ActuatorRuntimeKVTests(SimpleTestCase):
    """隔离存储验证业务接线；MySQL 原子性由 RuntimeKV 自身测试覆盖。"""

    def setUp(self):
        self.now = 0
        self.rows = {}
        namespace = RuntimeKV.namespace

        def make_store(module):
            real_store = namespace(module)

            def put(key, value, **kwargs):
                key = real_store._key(key)
                ttl = real_store._ttl(kwargs['ttl']) if 'ttl' in kwargs else real_store.policy['ttl']
                self.rows[(module, key)] = (real_store._value(value)['data'], self.now + ttl)

            def get(key, default=None):
                value, expires = self.rows.get((module, key), (default, self.now))
                return value if expires > self.now else default

            return SimpleNamespace(
                set=put, get=get,
                delete=lambda key: self.rows.pop((module, key), None),
            )

        patcher = patch.object(RuntimeKV, 'namespace', side_effect=make_store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_capabilities_round_trip_expiry_and_connection_isolation(self):
        connection_id = uuid4()
        SocketConnectionService.update_capabilities(
            connection_id, ['ui', 'ui'], {'ui': 2}, {'ui': 3},
        )
        self.assertTrue(SocketConnectionService.supports_task_type(str(connection_id), 'ui'))
        self.assertEqual(SocketConnectionService.capability_capacity(connection_id, 'ui'), 3)
        self.assertFalse(SocketConnectionService.supports_task_type(uuid4(), 'ui'))
        self.now = 90
        self.assertFalse(SocketConnectionService.supports_task_type(connection_id, 'ui'))
        self.assertEqual(SocketConnectionService.capability_capacity(connection_id, 'ui', 1), 1)

    def test_draining_expiry_delete_and_capability_independence(self):
        connection_id = str(uuid4())
        SocketConnectionService.update_capabilities(connection_id, ['ui'], {})
        SocketConnectionService.set_draining(connection_id, True)
        self.assertTrue(SocketConnectionService.is_draining(connection_id))
        SocketConnectionService.set_draining(connection_id, False)
        self.assertFalse(SocketConnectionService.is_draining(connection_id))
        self.assertTrue(SocketConnectionService.supports_task_type(connection_id, 'ui'))
        SocketConnectionService.set_draining(connection_id, True)
        self.now = 90
        self.assertTrue(SocketConnectionService.is_draining(connection_id))
        self.now = 600
        self.assertFalse(SocketConnectionService.is_draining(connection_id))

    def test_config_pending_callback_polling_and_expiry(self):
        view = SocketApiViews()
        for start, callback, poll in (
            (view.request_actuator_config, SystemConsumer.save_actuator_config_snapshot,
             view.get_actuator_config_result),
            (view.update_actuator_config, SystemConsumer.save_actuator_config_save_result,
             view.get_actuator_config_save_result),
        ):
            with self.subTest(action=start.__name__), patch.object(
                SocketConnectionService, 'require_actuator',
            ), patch(
                'src.apps.system.api.views.socket_api.SocketMessageService.send_socket_data',
            ) as send, patch.object(SystemConsumer, '_sync_socket_user_runtime_status'):
                response = start(SimpleNamespace(data={'username': 'executor', 'config': {}}))
                request_id = response.data['data']['request_id']
                request = SimpleNamespace(query_params={'request_id': request_id})
                self.assertEqual(poll(request).data['data'], {'status': 'pending', 'username': 'executor'})
                self.assertEqual(send.call_args.args[0].data.func_args['request_id'], request_id)
                callback({'request_id': request_id, 'username': 'executor', 'config': {'runtime': {}}})
                self.assertEqual(poll(request).data['data']['status'], 'success')
                self.assertEqual(poll(request).data['data']['config'], {'runtime': {}})
                self.now += 60
                self.assertEqual(poll(request).data['data'], {'status': 'expired'})

    def test_config_save_failure_and_request_type_isolation(self):
        ActuatorConfigRuntimeService.set_snapshot('same', {'status': 'pending'})
        with patch.object(SystemConsumer, '_sync_socket_user_runtime_status'):
            SystemConsumer.save_actuator_config_save_result({
                'request_id': 'same', 'username': 'executor', 'status': False, 'message': 'failed',
            })
        self.assertEqual(ActuatorConfigRuntimeService.get_snapshot('same'), {'status': 'pending'})
        self.assertEqual(ActuatorConfigRuntimeService.get_save_result('same')['status'], 'failed')
        self.assertIsNone(ActuatorConfigRuntimeService.get_snapshot('another'))

    def test_callback_without_request_id_does_not_write(self):
        SystemConsumer.save_actuator_config_snapshot({})
        SystemConsumer.save_actuator_config_save_result({})
        self.assertEqual(self.rows, {})

    def test_policies_are_ephemeral_and_config_is_sensitive(self):
        self.assertTrue(RUNTIME_KV_POLICIES[RuntimeKVNamespaceEnum.ACTUATOR_CONFIG.value]['sensitive'])
        for module in (RuntimeKVNamespaceEnum.ACTUATOR_CONFIG, RuntimeKVNamespaceEnum.EXECUTOR_STATE):
            self.assertFalse(RUNTIME_KV_POLICIES[module.value]['persistent'])

    def test_storage_failure_is_not_silently_fallback_to_django_cache(self):
        with patch.object(RuntimeKV, 'namespace', side_effect=OperationalError('unavailable')):
            with self.assertRaises(OperationalError):
                SocketConnectionService.set_draining('executor', True)
            with self.assertRaises(OperationalError):
                ActuatorConfigRuntimeService.set_snapshot('request', {'status': 'pending'})
