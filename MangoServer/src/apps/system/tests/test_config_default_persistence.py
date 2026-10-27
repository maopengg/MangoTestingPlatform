from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from src.apps.system.api.views.cache_data import CacheDataCRUD, CacheDataViews
from src.apps.system.enums import CacheDataKey2Enum
from src.apps.system.services.system_config import (
    API_WORKER_DESIRED_COUNT_DEFAULT,
    API_WORKER_DESIRED_COUNT_KEY,
    DEPRECATED_SYSTEM_CONFIG_KEYS,
    get_config_definition_map,
    SystemConfigDefinition,
    SystemConfigService,
)


class ConfigDefaultPersistenceTests(SimpleTestCase):
    def test_data_factory_retention_default_is_sixty_days(self):
        key = 'DATA_FACTORY_EXECUTION_RETENTION_DAYS'
        definition = get_config_definition_map()[key]
        self.assertEqual(definition.default_value, 60)
        self.assertEqual(SystemConfigService._definition_defaults(definition)['value'], '60')
        with patch.object(SystemConfigService, 'get_runtime_int', return_value=60) as read:
            self.assertEqual(SystemConfigService.get_ranged_int(key), 60)
        read.assert_called_once_with(key, default=60, min_value=1, max_value=3650)

    def test_existing_data_factory_retention_is_preserved(self):
        manager = self.sync('90', 60, key='DATA_FACTORY_EXECUTION_RETENTION_DAYS', update_user_id=7)
        self.assertFalse(any('pk' in call.kwargs for call in manager.filter.call_args_list))

    def test_obsolete_configs_are_not_registered_or_editable(self):
        definitions = get_config_definition_map()
        editable = SystemConfigService.editable_config_keys()
        self.assertTrue(DEPRECATED_SYSTEM_CONFIG_KEYS.isdisjoint(definitions))
        self.assertTrue(DEPRECATED_SYSTEM_CONFIG_KEYS.isdisjoint(editable))
        for key in DEPRECATED_SYSTEM_CONFIG_KEYS:
            with self.subTest(key=key):
                self.assertIsNotNone(SystemConfigService.validate_editable_config(key, 'test'))

    def test_only_registered_business_configs_can_be_edited(self):
        self.assertIn('EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES', SystemConfigService.editable_config_keys())
        self.assertIsNone(SystemConfigService.validate_editable_config('EXECUTOR_PYTEST_MAX_RUNTIME_MINUTES', '60'))
        for key in ('unknown_legacy_config', 'select_value', '__system_snowflake_next_tick__'):
            with self.subTest(key=key):
                self.assertNotIn(key, SystemConfigService.editable_config_keys())
                self.assertIsNotNone(SystemConfigService.validate_editable_config(key, 'test'))

    def test_method_cache_enum_only_contains_active_keys(self):
        self.assertEqual(
            {item.value for item in CacheDataKey2Enum},
            {'select_value', 'ass_select_value', 'test_data_select_value'},
        )

    @patch.object(SystemConfigService, 'sync_registered_configs')
    def test_config_list_and_grouped_only_query_registered_editable_keys(self, sync):
        for view_class, method in ((CacheDataCRUD, 'get'), (CacheDataViews, 'grouped')):
            with self.subTest(method=method), patch(
                'src.apps.system.api.views.cache_data.CacheData.objects',
            ) as manager:
                queryset = MagicMock()
                queryset.__iter__.return_value = iter([])
                queryset.count.return_value = 0
                manager.filter.return_value.exclude.return_value.order_by.return_value = queryset
                view = view_class()
                view.serializer_class = MagicMock()
                getattr(view, method)(SimpleNamespace())
                manager.filter.assert_called_once_with(
                    key__in=SystemConfigService.editable_config_keys(),
                    is_enabled=True,
                    management_level__gte=2,
                )

    def test_legacy_pytest_git_url_is_disabled_on_initialization(self):
        self.assertIn('PYTEST_GIT_URL', DEPRECATED_SYSTEM_CONFIG_KEYS)
        manager = self.sync(None, 120, created=True)
        manager.filter.assert_any_call(key__in=DEPRECATED_SYSTEM_CONFIG_KEYS, is_enabled=True)
        manager.filter.return_value.update.assert_any_call(is_enabled=False)

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
