import copy
import hashlib
import json
from datetime import datetime, timezone
from contextlib import nullcontext
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService as Health
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class HealthIncidentTests(SimpleTestCase):
    def setUp(self):
        self.store = AtomicMemoryStore()
        self.scope = 'datasource:' + 'a' * 32
        self.key = 'incident:' + hashlib.sha256(self.scope.encode()).hexdigest()[:32]
        for guard in (
            patch.object(Governor, 'store', return_value=self.store),
            patch.object(self.store, 'get', create=True,
                         side_effect=lambda key: copy.deepcopy(self.store.values.get(key))),
        ):
            guard.start()
            self.addCleanup(guard.stop)
        guard = patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEventService.record_health_transition')
        self.delivery = guard.start()
        self.addCleanup(guard.stop)

    def observe(self, active=True, **kwargs):
        return Health.observe(self.scope, active=active, metrics={'unconfirmed_count': int(active)}, **kwargs)

    def test_parallel_monitoring_deduplicates_and_recovery_updates_same_event(self):
        with ThreadPoolExecutor(max_workers=10) as pool:
            list(pool.map(lambda _: self.observe(), range(100)))
        self.delivery.assert_called_once()
        original = self.delivery.call_args.kwargs
        self.assertEqual(self.store.values[self.key]['occurrences'], 1)
        self.observe(False)
        resolved = self.delivery.call_args.kwargs
        self.assertEqual(original['request_path'], resolved['request_path'])
        self.assertEqual(original['message'], resolved['message'])
        self.assertFalse(json.loads(resolved['trace'])['active'])
        self.assertEqual(self.store.values[self.key]['delivered_revision'], 2)
        self.observe(False)
        self.assertEqual(self.delivery.call_count, 2)

    def test_delivery_failure_is_persistent_and_retried_without_reopening(self):
        self.delivery.side_effect = RuntimeError('AUTO_DELIVERY_FAILURE')
        with self.assertRaises(RuntimeError):
            self.observe()
        state = self.store.values[self.key]
        self.assertTrue(state['active'])
        self.assertEqual(state['delivered_revision'], 0)
        self.delivery.side_effect = None
        self.observe()
        self.assertEqual(self.store.values[self.key]['delivered_revision'], 1)
        self.assertEqual(self.store.values[self.key]['occurrences'], 1)

    def test_publisher_crash_requires_lease_expiry_not_duplicate_parallel_delivery(self):
        self.observe()
        state = self.store.values[self.key]
        state.update(delivered_revision=0, publisher='b' * 32, publish_until=self.store.now + 30)
        self.delivery.reset_mock()
        self.observe()
        self.delivery.assert_not_called()
        self.store.now += 31
        self.observe()
        self.delivery.assert_called_once()

    def test_unobserved_healthy_state_does_not_create_incident(self):
        self.assertIsNone(self.observe(False))
        self.assertNotIn(self.key, self.store.values)
        self.delivery.assert_not_called()

    def test_pending_delivery_cannot_overwrite_newer_observation(self):
        self.observe()
        self.observe(False)
        last_seen = self.store.values[self.key]['last_seen_at']
        self.store.now += 60
        self.observe(True, delivery_only=True)
        self.assertFalse(self.store.values[self.key]['active'])
        self.assertEqual(self.store.values[self.key]['last_seen_at'], last_seen)
        self.assertEqual(self.store.values[self.key]['occurrences'], 1)

    def test_background_retry_survives_producer_exit_without_fake_fresh_observation(self):
        self.delivery.side_effect = RuntimeError('AUTO_DELIVERY')
        with self.assertRaises(RuntimeError):
            self.observe()
        last_seen = self.store.values[self.key]['last_seen_at']
        self.store.now += 60
        self.store.name = 'datasource_governor'
        row = SimpleNamespace(key=self.key, value={'data': copy.deepcopy(self.store.values[self.key])},
                              kv_now=datetime.fromtimestamp(self.store.now, timezone.utc))
        self.delivery.side_effect = None
        with patch.object(self.store, 'scan', create=True,
                          return_value={'items': [{'key': self.key}], 'next_cursor': 88}), \
                patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.entries', return_value=[row]):
            self.assertEqual(Health.retry_pending(30), 88)
        self.assertEqual(self.store.values[self.key]['delivered_revision'], 1)
        self.assertEqual(self.store.values[self.key]['last_seen_at'], last_seen)

    def test_closed_incident_retention_cannot_remove_reopened_state(self):
        self.observe()
        self.observe(False)
        old = copy.deepcopy(self.store.values[self.key])
        self.store.now += 61 * 86400
        row = SimpleNamespace(key=self.key, value={'data': old},
                              kv_now=datetime.fromtimestamp(self.store.now, timezone.utc))
        self.observe()
        self.store.name = 'datasource_governor'
        entry = SimpleNamespace(found=True, value=self.store.values[self.key], version='AUTO_VERSION')
        with patch.object(self.store, 'scan', create=True,
                          return_value={'items': [{'key': self.key}], 'next_cursor': None}), \
                patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.entries', return_value=[row]), \
                patch.object(self.store, 'get_entry', create=True, return_value=entry), \
                patch.object(self.store, 'delete_if_version', create=True) as delete:
            Health.retry_pending()
        delete.assert_not_called()

    def test_corrupt_incident_does_not_hide_other_pending_notifications(self):
        self.delivery.side_effect = RuntimeError('AUTO_DELIVERY')
        with self.assertRaises(RuntimeError):
            self.observe()
        self.delivery.side_effect = None
        self.store.name = 'datasource_governor'
        rows = [SimpleNamespace(id=1, key='incident:invalid', value={'data': {'invalid': True}}),
                SimpleNamespace(id=2, key=self.key, value={'data': self.store.values[self.key]})]
        with patch.object(self.store, 'scan', create=True,
                          return_value={'items': [{'key': row.key} for row in rows], 'next_cursor': 2}), \
                patch('src.apps.system.selectors.runtime_kv.RuntimeKVSelector.entries', return_value=rows):
            self.assertEqual(Health.retry_pending(), 2)
        self.assertEqual(self.store.values[self.key]['delivered_revision'], 1)


class HealthEventRevisionTests(SimpleTestCase):
    def test_stale_and_duplicate_publication_cannot_overwrite_recovered_event(self):
        from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService as Events
        from src.common.enums.system_error import SystemErrorEventSource
        with patch('src.apps.system.services.runtime_center.system_error_event.transaction.atomic',
                   side_effect=lambda: nullcontext()), \
                patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEvent.objects') as rows, \
                patch.object(Events, 'record') as record:
            rows.select_for_update.return_value.filter.return_value.only.return_value.first.return_value = SimpleNamespace(
                traceback=json.dumps({'revision': 2, 'active': False}))
            for revision in (1, 2, 3):
                Events.record_health_transition(revision=revision, service_name='scheduler-service',
                    source=SystemErrorEventSource.SCHEDULER, request_path='datasource-health/' + 'a' * 32,
                    message='AUTO_HEALTH', trace=json.dumps({'revision': revision}))
            record.assert_called_once()
            self.assertEqual(json.loads(record.call_args.kwargs['trace'])['revision'], 3)

    def test_new_generation_after_retention_is_not_hidden_by_old_high_revision(self):
        from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService as Events
        from src.common.enums.system_error import SystemErrorEventSource
        with patch('src.apps.system.services.runtime_center.system_error_event.transaction.atomic',
                   side_effect=lambda: nullcontext()), \
                patch('src.apps.system.services.runtime_center.system_error_event.SystemErrorEvent.objects') as rows, \
                patch.object(Events, 'record') as record:
            rows.select_for_update.return_value.filter.return_value.only.return_value.first.return_value = SimpleNamespace(
                traceback=json.dumps({'generation': 100, 'revision': 99, 'active': False}))
            Events.record_health_transition(generation=200, revision=1, service_name='scheduler-service',
                source=SystemErrorEventSource.SCHEDULER, request_path='datasource-health/' + 'a' * 32,
                message='AUTO_HEALTH', trace=json.dumps({'generation': 200, 'revision': 1}))
            record.assert_called_once()
