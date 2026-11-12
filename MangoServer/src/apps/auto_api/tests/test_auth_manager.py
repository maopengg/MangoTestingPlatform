from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.auto_api.enums import ApiAuthRefreshModeEnum
from src.apps.auto_api.services.execution.base.api_base_test_setup.auth_manager import ApiAuthManager


class ApiAuthManagerCacheAvailabilityTests(SimpleTestCase):
    def setUp(self):
        patcher = patch.object(ApiAuthManager, '_target_scope', return_value=None)
        self.scope = patcher.start()
        self.addCleanup(patcher.stop)

    def test_target_scope_mismatch_never_reuses_auth_cache(self):
        self.scope.return_value = 'south'
        config = SimpleNamespace(cache_data={'Authorization': 'token', '__mango_target_scope__': 'east'},
                                 refresh_mode=ApiAuthRefreshModeEnum.MANUAL.value)
        self.assertFalse(ApiAuthManager()._is_cache_available(config))
        config.cache_data['__mango_target_scope__'] = 'south'
        self.assertTrue(ApiAuthManager()._is_cache_available(config))

    def test_manual_cache_ignores_expired_time(self):
        config = SimpleNamespace(
            cache_data={'Authorization': 'Bearer token'},
            expires_at=timezone.now() - timedelta(days=1),
            refresh_margin=5,
            refresh_mode=ApiAuthRefreshModeEnum.MANUAL.value,
        )

        self.assertTrue(ApiAuthManager()._is_cache_available(config))

    def test_manual_cache_still_requires_cache_data(self):
        config = SimpleNamespace(
            cache_data={},
            expires_at=None,
            refresh_margin=5,
            refresh_mode=ApiAuthRefreshModeEnum.MANUAL.value,
        )

        self.assertFalse(ApiAuthManager()._is_cache_available(config))

    def test_non_manual_cache_still_checks_expired_time(self):
        config = SimpleNamespace(
            cache_data={'Authorization': 'Bearer token'},
            expires_at=timezone.now() - timedelta(minutes=1),
            refresh_margin=5,
            refresh_mode=ApiAuthRefreshModeEnum.PASSIVE.value,
        )

        self.assertFalse(ApiAuthManager()._is_cache_available(config))
