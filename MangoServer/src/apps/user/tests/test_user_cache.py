from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.user.exceptions import UserError
from src.apps.user.services.environment import UserEnvironmentService
from src.apps.user.services.user_cache import UserCacheService


class UserCacheServiceTests(SimpleTestCase):
    def setUp(self):
        aliases = patch(
            'src.apps.system.services.system_config.SystemConfigService.get_environment_display_names',
            return_value={},
        )
        aliases.start()
        self.addCleanup(aliases.stop)

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

    def test_invalid_legacy_environment_becomes_unselected_once(self):
        for value in (99, -1, 'missing', [], {}):
            with self.subTest(value=value):
                user = self.user(selected_environment=value)
                self.assertIsNone(UserCacheService.selected_environment(user))
                self.assertIsNone(UserCacheService.selected_environment(user))
                self.assertEqual(user.selected_environment, value)
                user.save.assert_called_once_with(update_fields=['config', 'update_time'])

    def test_invalid_cached_environment_does_not_fall_back_to_legacy_value(self):
        user = self.user(selected_environment=2)
        UserCacheService.set_selected_environment(user, 1)
        item = user.config['personal_cache']['preferences']['items']['selected_environment']
        item['value'] = 99
        user.config['unrelated'] = {'keep': True}

        groups = UserCacheService.grouped(user)

        self.assertIsNone(UserCacheService.selected_environment(user))
        self.assertEqual(groups[0]['items'][0]['display_value'], '未选择测试环境')
        self.assertFalse(groups[0]['items'][0]['has_value'])
        self.assertEqual(user.config['unrelated'], {'keep': True})
        user.save.assert_called_once_with(update_fields=['config', 'update_time'])

    def test_cached_string_environment_is_normalized_without_losing_zero(self):
        user = self.user()
        UserCacheService.set_selected_environment(user, 1)
        user.config['personal_cache']['preferences']['items']['selected_environment']['value'] = '0'
        self.assertEqual(UserCacheService.selected_environment(user), 0)
        self.assertIs(type(UserCacheService.selected_environment(user)), int)
        user.save.assert_called_once_with(update_fields=['config', 'update_time'])

    def test_cleared_environment_does_not_restore_legacy_value(self):
        user = self.user(selected_environment=2)
        UserCacheService.set_selected_environment(user, None)
        self.assertIsNone(UserCacheService.selected_environment(user))
        user.save.assert_not_called()

    def test_explicit_environment_updates_still_reject_invalid_values(self):
        user = self.user()
        for value in (99, -1, 'missing'):
            with self.subTest(value=value):
                with self.assertRaises(UserError) as error:
                    UserEnvironmentService.switch(user, value)
                self.assertEqual(error.exception.code, 41009)
                with self.assertRaises(UserError):
                    UserCacheService.set_selected_environment(user, value)
        user.save.assert_not_called()

    def test_environment_id_validation_does_not_read_display_configuration(self):
        with patch(
            'src.apps.system.services.system_config.SystemConfigService.get_environment_display_names',
            side_effect=AssertionError('环境 ID 校验不应查询显示配置'),
        ):
            for value in range(6):
                self.assertEqual(UserEnvironmentService.normalize_environment(value), value)
