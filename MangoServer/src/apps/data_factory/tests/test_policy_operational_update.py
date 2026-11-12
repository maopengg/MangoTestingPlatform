import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from mangotools.enums import CacheValueTypeEnum

from src.apps.system.exceptions import SystemError
from src.apps.system.services.configuration.cache_data import CacheDataService
from src.apps.system.services.configuration.system_config import SystemConfigService


class OperationalPolicyUpdateTests(SimpleTestCase):
    def setUp(self):
        self.old = {'version': 2, 'pool_size': 2, 'mysql': {'connections': 12}, 'cleanup_consumer_threads': 2}
        self.config = SimpleNamespace(value=json.dumps(self.old), value_type=CacheValueTypeEnum.DICT.value,
                                      key='DATASOURCE_PERFORMANCE_POLICY', save=Mock())
        for guard in (patch('src.apps.system.services.configuration.cache_data.CacheData.objects'),
                      patch.object(SystemConfigService, 'validate_editable_config', return_value=None),
                      patch.object(SystemConfigService, 'validate_datasource_policy_transition', return_value=None),
                      patch.object(SystemConfigService, 'invalidate')):
            mocked = guard.start()
            self.addCleanup(guard.stop)
            if guard.attribute == 'objects':
                mocked.select_for_update.return_value.get.return_value = self.config

    def update(self, changes):
        return CacheDataService.update_datasource_policy.__func__.__wrapped__(
            CacheDataService, changes, update_user_id=4)

    def test_budget_update_keeps_pool_and_cleanup_threads_and_invalidates_cache(self):
        saved = self.update({'mysql': {'connections': 20}})
        self.assertEqual(saved['pool_size'], 2)
        self.assertEqual(saved['cleanup_consumer_threads'], 2)
        self.assertEqual(self.config.update_user_id, 4)
        SystemConfigService.validate_datasource_policy_transition.assert_called_once_with(self.config, saved)
        SystemConfigService.invalidate.assert_called_once_with(self.config.key)

    def test_pool_transition_rejection_never_saves_or_invalidates_config(self):
        SystemConfigService.validate_datasource_policy_transition.return_value = 'wait for verified drain'
        with self.assertRaises(SystemError):
            self.update({'pool_size': 4})
        self.config.save.assert_not_called()
        SystemConfigService.invalidate.assert_not_called()

    def test_invalid_budget_never_bypasses_schema_validation(self):
        SystemConfigService.validate_editable_config.return_value = 'invalid reservation'
        with self.assertRaises(SystemError):
            self.update({'mysql': {'connections': 0}})
        SystemConfigService.validate_datasource_policy_transition.assert_not_called()
        self.config.save.assert_not_called()
