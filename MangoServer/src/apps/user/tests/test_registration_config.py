from types import SimpleNamespace
from unittest.mock import call, patch

from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from mangotools.enums import CacheValueTypeEnum
from rest_framework.test import APIRequestFactory

from src.apps.system.models import CacheData
from src.apps.system.services.system_config import SystemConfigService
from src.apps.user.api.views.user import LoginViews
from src.apps.user.middleware.permission import MenuActionPermission


class RegistrationConfigTests(SimpleTestCase):
    path = '/api/user/registration-config'

    @patch('src.apps.system.services.system_config.CacheData.objects.get')
    def test_database_switch_and_message_are_the_only_public_config_values(self, get_config):
        def stored_value(*, key):
            return {
                'ALLOW_HOME_REGISTRATION': SimpleNamespace(value='false', value_type=CacheValueTypeEnum.BOOL.value),
                'REGISTRATION_DISABLED_MESSAGE': SimpleNamespace(value='请联系管理员', value_type=CacheValueTypeEnum.STR.value),
            }[key]

        get_config.side_effect = stored_value
        result = SystemConfigService.get_registration_config()

        self.assertEqual(result, {'allow_registration': False, 'disabled_message': '请联系管理员'})
        self.assertEqual(get_config.call_args_list, [
            call(key='ALLOW_HOME_REGISTRATION'), call(key='REGISTRATION_DISABLED_MESSAGE'),
        ])

    @override_settings(ALLOW_HOME_REGISTRATION=False, REGISTRATION_DISABLED_MESSAGE='旧环境配置不可生效')
    @patch('src.apps.system.services.system_config.CacheData.objects.get', side_effect=CacheData.DoesNotExist)
    def test_missing_rows_use_registered_defaults_not_environment_settings(self, _get_config):
        result = SystemConfigService.get_registration_config()

        self.assertTrue(result['allow_registration'])
        self.assertEqual(result['disabled_message'], '当前平台未开放自助注册，请联系管理员开通账号。')

    @patch('src.apps.system.services.system_config.SystemConfigService.get_registration_config')
    def test_public_route_returns_only_registration_config_without_login_or_caching(self, config):
        config.return_value = {'allow_registration': False, 'disabled_message': '注册已关闭'}
        request = APIRequestFactory().get(self.path, {'key': 'AI_API_KEY'}, HTTP_AUTHORIZATION='expired-token')
        response = resolve(self.path).func(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['data'], config.return_value)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertIn(self.path, MenuActionPermission.PUBLIC_PATH_PREFIXES)
        config.assert_called_once_with()

    @patch('src.apps.system.services.system_config.SystemConfigService.get_registration_config')
    def test_public_route_does_not_expose_write_methods(self, config):
        response = resolve(self.path).func(APIRequestFactory().post(self.path, {}, format='json'))

        self.assertEqual(response.status_code, 405)
        config.assert_not_called()

    @patch('src.apps.system.services.system_config.SystemConfigService.get_registration_config')
    @patch.object(LoginViews, '_is_super_admin_registration', return_value=False)
    def test_registration_rechecks_the_switch_after_form_opened(self, _admin, config):
        config.side_effect = [
            {'allow_registration': True, 'disabled_message': '注册已关闭'},
            {'allow_registration': False, 'disabled_message': '注册已关闭'},
        ]
        view = LoginViews()
        request = SimpleNamespace(data={})

        self.assertTrue(view.registration_config(request).data['data']['allow_registration'])
        response = view.register(request)

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(response.data['msg'], '注册已关闭')
        self.assertEqual(config.call_count, 2)
