from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from src.apps.user.services.environment import UserEnvironmentService
from src.apps.user.services.user_cache import UserCacheService


class UserCacheServiceTests(SimpleTestCase):
    @staticmethod
    def user(*, selected_environment=1, config=None):
        return SimpleNamespace(
            id=4,
            selected_environment=selected_environment,
            config=config or {},
            update_user_id=None,
            save=MagicMock(),
        )

    def test_legacy_environment_is_migrated_to_personal_cache_once(self):
        user = self.user(selected_environment=1)

        selected_environment = UserCacheService.selected_environment(user)

        self.assertEqual(selected_environment, 1)
        self.assertEqual(
            user.config['personal_cache']['preferences']['items']['selected_environment']['value'],
            1,
        )
        user.save.assert_called_once_with(update_fields=['config', 'update_time'])

    def test_switch_environment_only_writes_config_and_keeps_legacy_field_unchanged(self):
        user = self.user(selected_environment=2)

        result = UserEnvironmentService.switch(user, 0, operator_id=4)

        self.assertEqual(result['selected_environment'], 0)
        self.assertEqual(user.selected_environment, 2)
        self.assertEqual(UserCacheService.selected_environment(user), 0)
        user.save.assert_called_once_with(update_fields=['config', 'update_user', 'update_time'])

    def test_user_can_clear_cache_value(self):
        user = self.user(selected_environment=None)
        UserCacheService.set_selected_environment(user, 1)

        count = UserCacheService.clear(
            user,
            group_key='preferences',
            cache_key='selected_environment',
        )
        self.assertEqual(count, 1)
        self.assertIsNone(UserCacheService.selected_environment(user))

    def test_grouped_response_contains_display_value(self):
        user = self.user(selected_environment=None)
        UserCacheService.set_selected_environment(user, 1)

        groups = UserCacheService.grouped(user)

        self.assertEqual(groups[0]['title'], '偏好设置')
        self.assertEqual(groups[0]['items'][0]['display_value'], '预发环境')
