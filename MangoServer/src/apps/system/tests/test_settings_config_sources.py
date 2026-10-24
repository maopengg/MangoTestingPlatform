import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase
from mangotools.enums import CacheValueTypeEnum

from src.apps.system.models import CacheData
from src.apps.system.services.system_config import SystemConfigService, get_config_definition_map
from src.apps.test_center.api.views.index import IndexViews
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.apps.test_center.services.test_suite.effectiveness import AutomationEffectivenessService
from src.apps.test_center.services.test_suite.report_overview import TestSuiteReportOverviewService


class SettingsConfigSourceTests(SimpleTestCase):
    defaults = {
        'RESULT_DATA_RETENTION_DAYS': 60,
        'HOME_INDEX_CACHE_SECONDS': 300,
        'HOME_OVERVIEW_CACHE_SECONDS': 600,
        'REPORT_OVERVIEW_CACHE_SECONDS': 600,
        'EFFECTIVENESS_CACHE_SECONDS': 600,
        'EFFECTIVENESS_AI_CACHE_SECONDS': 3600,
    }

    def test_missing_database_rows_use_the_same_defaults_as_initialization(self):
        definitions = get_config_definition_map()
        with patch.dict(SystemConfigService._runtime_int_cache, {}, clear=True), \
                patch('src.apps.system.services.system_config.CacheData.objects.get', side_effect=CacheData.DoesNotExist):
            for key, expected in self.defaults.items():
                with self.subTest(key=key):
                    self.assertEqual(definitions[key].default_value, expected)
                    self.assertEqual(SystemConfigService.get_ranged_int(key), expected)
            self.assertEqual(ExecutionResultService.retention_days(), 60)

    def test_user_values_override_defaults_and_cache_zero_is_preserved(self):
        def stored(*, key):
            value = '90' if key == 'RESULT_DATA_RETENTION_DAYS' else '0'
            return SimpleNamespace(value=value, value_type=CacheValueTypeEnum.INT.value)

        with patch.dict(SystemConfigService._runtime_int_cache, {}, clear=True), \
                patch('src.apps.system.services.system_config.CacheData.objects.get', side_effect=stored):
            self.assertEqual(ExecutionResultService.retention_days(), 90)
            for key in self.defaults:
                if key != 'RESULT_DATA_RETENTION_DAYS':
                    self.assertEqual(SystemConfigService.get_ranged_int(key), 0)

    def test_home_cache_uses_the_corresponding_database_config(self):
        for action, config_key in (
            ('case_sum', 'HOME_INDEX_CACHE_SECONDS'),
            ('case_sum_v2', 'HOME_OVERVIEW_CACHE_SECONDS'),
        ):
            with self.subTest(action=action), \
                    patch.object(IndexViews, '_index_cache_key', return_value='test-home-cache'), \
                    patch.object(cache, 'get', return_value=None), \
                    patch.object(cache, 'set') as save_cache, \
                    patch.object(SystemConfigService, 'get_ranged_int', return_value=47) as config:
                data = IndexViews._cached_data(None, action, lambda: {'value': 1})
                config.assert_called_once_with(config_key)
                save_cache.assert_called_once_with('test-home-cache', data, 47)

    def test_report_and_effectiveness_cache_allow_database_config_to_disable_caching(self):
        for service, config_key in (
            (TestSuiteReportOverviewService, 'REPORT_OVERVIEW_CACHE_SECONDS'),
            (AutomationEffectivenessService, 'EFFECTIVENESS_CACHE_SECONDS'),
        ):
            with self.subTest(service=service.__name__), \
                    patch.object(service, '_cache_key', return_value='test-overview-cache'), \
                    patch.object(service, '_build_overview', return_value={'value': 1}), \
                    patch.object(cache, 'get', return_value=None), \
                    patch.object(cache, 'set') as save_cache, \
                    patch.object(SystemConfigService, 'get_ranged_int', return_value=0) as config:
                data = service.overview(None)
                config.assert_called_once_with(config_key)
                save_cache.assert_called_once_with('test-overview-cache', data, 0)

    @staticmethod
    def load_storage_settings(environment, **overrides):
        env = dict(os.environ, DJANGO_ENV=environment)
        for key in ('RESULT_DATA_TO_FILE', 'RESULT_DATA_FILE_PREFIX',
                    'RESULT_DATA_DETAIL_INLINE_MAX_SIZE', 'UI_EXECUTION_ARTIFACT_ROOT_DIR'):
            env.pop(key, None)
        env.update(overrides)
        script = (
            'import json; from src import settings; '
            'print(json.dumps([settings.RESULT_DATA_TO_FILE, settings.RESULT_DATA_FILE_PREFIX, '
            'settings.RESULT_DATA_DETAIL_INLINE_MAX_SIZE, settings.UI_EXECUTION_ARTIFACT_ROOT_DIR]))'
        )
        output = subprocess.check_output(
            [sys.executable, '-c', script], env=env,
            cwd=Path(__file__).resolve().parents[4], text=True,
        )
        return json.loads(output)

    def test_all_environments_load_the_same_common_storage_defaults(self):
        for environment in ('dev', 'test', 'master'):
            with self.subTest(environment=environment):
                self.assertEqual(self.load_storage_settings(environment), [True, 'result', 5 * 1024 * 1024, 'uitest'])

    def test_deployment_environment_overrides_are_still_supported(self):
        self.assertEqual(self.load_storage_settings(
            'dev', RESULT_DATA_TO_FILE='false', RESULT_DATA_FILE_PREFIX='custom-result',
            RESULT_DATA_DETAIL_INLINE_MAX_SIZE='1024', UI_EXECUTION_ARTIFACT_ROOT_DIR='custom-ui',
        ), [False, 'custom-result', 1024, 'custom-ui'])

    def test_obsolete_business_settings_are_removed(self):
        for name in (
            'RESULT_DATA_FILE_EXPIRE_DAYS',
            'HOME_INDEX_CACHE_TIMEOUT_SECONDS',
            'HOME_INDEX_OVERVIEW_CACHE_TIMEOUT_SECONDS',
            'TEST_REPORT_OVERVIEW_CACHE_TIMEOUT_SECONDS',
            'AUTOMATION_EFFECTIVENESS_CACHE_TIMEOUT_SECONDS',
            'AUTOMATION_EFFECTIVENESS_AI_CACHE_TIMEOUT_SECONDS',
        ):
            self.assertFalse(hasattr(settings, name), name)
