from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from src.apps.system.services.system_config import (
    API_WORKER_DESIRED_COUNT_DEFAULT,
    API_WORKER_DESIRED_COUNT_KEY,
    SystemConfigDefinition,
    SystemConfigService,
)


class ConfigDefaultPersistenceTests(SimpleTestCase):
    def sync(self, stored, default, *, created=False, key='TEST_CONFIG', update_user_id=None):
        definition = SystemConfigDefinition(key=key, describe='Test', group='system', default_value=default)
        obj = SimpleNamespace(pk=1, **SystemConfigService._definition_defaults(definition))
        obj.value = stored
        obj.update_user_id = update_user_id
        obj.save = Mock()
        with ExitStack() as stack:
            prefix = 'src.apps.system.services.system_config.'
            stack.enter_context(patch(prefix + 'SYSTEM_CONFIG_REGISTRY', [definition]))
            stack.enter_context(patch(prefix + 'SYSTEM_INTERNAL_CONFIG_REGISTRY', []))
            manager = stack.enter_context(patch(prefix + 'CacheData.objects'))
            manager.get_or_create.return_value = (obj, created)
            for name in ('normalize_ai_timeout', 'normalize_api_worker_thread_pool_size',
                         'normalize_data_factory_validation_environments', 'normalize_ui_locator_timeouts',
                         'normalize_execution_settings', 'normalize_ranged_int_configs'):
                stack.enter_context(patch.object(SystemConfigService, name))
            SystemConfigService.sync_registered_configs()
        return manager

    def test_new_config_is_created_with_persisted_default(self):
        manager = self.sync(None, 120, created=True)
        self.assertEqual(manager.get_or_create.call_args.kwargs['defaults']['value'], '120')

    def test_legacy_level_four_is_normalized_to_standard(self):
        manager = self.sync(None, 120, created=True)

        manager.filter.assert_any_call(management_level=4)
        manager.filter.return_value.update.assert_any_call(management_level=3)

    def test_missing_values_are_conditionally_backfilled(self):
        for empty in (None, ''):
            with self.subTest(value=empty):
                manager = self.sync(empty, 120)
                manager.filter.assert_any_call(pk=1, value=empty)
                manager.filter.return_value.update.assert_any_call(value='120')

    def test_existing_custom_zero_false_and_container_values_are_preserved(self):
        for value in ('45', '0', 0, False, 'false', '[]', '{}'):
            with self.subTest(value=value):
                manager = self.sync(value, 120)
                self.assertFalse(any('pk' in call.kwargs for call in manager.filter.call_args_list))

    def test_unconfigured_credentials_without_defaults_remain_empty(self):
        manager = self.sync(None, None)
        self.assertFalse(any('pk' in call.kwargs for call in manager.filter.call_args_list))

    def test_zero_and_false_defaults_are_not_skipped(self):
        for default in (0, False):
            with self.subTest(default=default):
                manager = self.sync(None, default)
                manager.filter.return_value.update.assert_any_call(value=str(default))

    def test_old_automatic_api_worker_default_is_upgraded_to_five(self):
        manager = self.sync(
            '1',
            API_WORKER_DESIRED_COUNT_DEFAULT,
            key=API_WORKER_DESIRED_COUNT_KEY,
        )

        manager.filter.assert_any_call(
            pk=1,
            update_user__isnull=True,
            value='1',
        )
        manager.filter.return_value.update.assert_any_call(
            value=str(API_WORKER_DESIRED_COUNT_DEFAULT),
        )

    def test_user_modified_api_worker_capacity_is_preserved(self):
        manager = self.sync(
            '1',
            API_WORKER_DESIRED_COUNT_DEFAULT,
            key=API_WORKER_DESIRED_COUNT_KEY,
            update_user_id=7,
        )

        self.assertFalse(
            any(
                call.kwargs.get('update_user__isnull') is True
                for call in manager.filter.call_args_list
            )
        )

    def test_registration_default_is_persisted_as_enabled(self):
        manager = self.sync(None, True, key='ALLOW_HOME_REGISTRATION', created=True)
        self.assertEqual(manager.get_or_create.call_args.kwargs['defaults']['value'], 'True')

    def test_administrator_disabled_registration_is_not_reset_during_initialization(self):
        manager = self.sync('false', True, key='ALLOW_HOME_REGISTRATION', update_user_id=7)
        self.assertFalse(any('pk' in item.kwargs for item in manager.filter.call_args_list))

    def test_ui_artifact_retention_default_is_persisted(self):
        manager = self.sync(None, 30, key='UI_ARTIFACT_RETENTION_DAYS', created=True)
        self.assertEqual(manager.get_or_create.call_args.kwargs['defaults']['value'], '30')

    def test_user_modified_ui_artifact_retention_is_not_overwritten(self):
        manager = self.sync('60', 30, key='UI_ARTIFACT_RETENTION_DAYS', update_user_id=7)
        self.assertFalse(any('pk' in item.kwargs for item in manager.filter.call_args_list))
