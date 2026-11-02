from types import SimpleNamespace
from unittest.mock import call, patch

from django.test import SimpleTestCase, override_settings
from django.urls import resolve
from mangotools.enums import CacheValueTypeEnum
from rest_framework.test import APIRequestFactory

from src.apps.system.models import CacheData
from src.apps.system.services.system_config import SystemConfigService, get_config_definition_map
from src.apps.user.api.views.user import LoginViews
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.enums.permission import HttpPermissionBoundaryEnum
from src.apps.user.services.http_permission_boundaries import HTTP_PERMISSION_BOUNDARIES


class RegistrationConfigTests(SimpleTestCase):
    path = '/api/user/registration-config'

    def test_display_switches_are_editable_boolean_configs_enabled_by_default(self):
        definitions = get_config_definition_map()
        for key in ('SHOW_LOGIN_AUTHOR_INFO', 'SHOW_HOME_AUTHOR_POPUP'):
            with self.subTest(key=key):
                definition = definitions[key]
                self.assertIs(definition.default_value, True)
                self.assertEqual(definition.value_type, CacheValueTypeEnum.BOOL.value)
                self.assertEqual(definition.group, 'access')
                self.assertIn(key, SystemConfigService.editable_config_keys())

    @patch('src.apps.system.services.system_config.CacheData.objects.get')
    def test_database_switch_message_and_author_visibility_are_public(self, get_config):
        def stored_value(*, key):
            return {
                'ALLOW_HOME_REGISTRATION': SimpleNamespace(value='false', value_type=CacheValueTypeEnum.BOOL.value),
                'REGISTRATION_DISABLED_MESSAGE': SimpleNamespace(value='请联系管理员', value_type=CacheValueTypeEnum.STR.value),
                'SHOW_LOGIN_AUTHOR_INFO': SimpleNamespace(value='false', value_type=CacheValueTypeEnum.BOOL.value),
                'SHOW_HOME_AUTHOR_POPUP': SimpleNamespace(value='false', value_type=CacheValueTypeEnum.BOOL.value),
                'PLATFORM_NAME': SimpleNamespace(value='演示测试平台', value_type=CacheValueTypeEnum.STR.value),
                'PLATFORM_NAME_EN': SimpleNamespace(value='ExampleTestingPlatform', value_type=CacheValueTypeEnum.STR.value),
            }[key]

        get_config.side_effect = stored_value
        result = SystemConfigService.get_registration_config()

        self.assertEqual(result, {
            'allow_registration': False, 'disabled_message': '请联系管理员',
            'show_author_info': False, 'show_home_author_popup': False,
            'platform_name': '演示测试平台', 'platform_name_en': 'ExampleTestingPlatform',
        })
        self.assertEqual(get_config.call_args_list, [
            call(key='ALLOW_HOME_REGISTRATION'), call(key='REGISTRATION_DISABLED_MESSAGE'),
            call(key='SHOW_LOGIN_AUTHOR_INFO'),
            call(key='SHOW_HOME_AUTHOR_POPUP'),
            call(key='PLATFORM_NAME'), call(key='PLATFORM_NAME_EN'),
        ])

    @override_settings(ALLOW_HOME_REGISTRATION=False, REGISTRATION_DISABLED_MESSAGE='旧环境配置不可生效')
    @patch('src.apps.system.services.system_config.CacheData.objects.get', side_effect=CacheData.DoesNotExist)
    def test_missing_rows_use_registered_defaults_not_environment_settings(self, _get_config):
        result = SystemConfigService.get_registration_config()

        self.assertTrue(result['allow_registration'])
        self.assertTrue(result['show_author_info'])
        self.assertTrue(result['show_home_author_popup'])
        self.assertEqual(result['platform_name'], '芒果测试平台')
        self.assertEqual(result['platform_name_en'], 'mango-test-platform')
        self.assertEqual(result['disabled_message'], '当前平台未开放自助注册，请联系管理员开通账号。')

    @patch('src.apps.system.services.system_config.SystemConfigService.get_registration_config')
    def test_public_route_returns_only_registration_config_without_login_or_caching(self, config):
        config.return_value = {
            'allow_registration': False, 'disabled_message': '注册已关闭',
            'show_author_info': True, 'show_home_author_popup': False,
        }
        request = APIRequestFactory().get(self.path, {'key': 'AI_API_KEY'}, HTTP_AUTHORIZATION='expired-token')
        response = resolve(self.path).func(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['data'], config.return_value)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(HTTP_PERMISSION_BOUNDARIES[(f'{LoginViews.__module__}.{LoginViews.__name__}', 'registration_config', 'get')],
                         HttpPermissionBoundaryEnum.PUBLIC)
        config.assert_called_once_with()

    @patch('src.apps.system.services.system_config.SystemConfigService.get_registration_config')
    def test_public_route_does_not_expose_write_methods(self, config):
        response = resolve(self.path).func(APIRequestFactory().post(self.path, {}, format='json'))

        self.assertNotEqual(response.data['code'], 200)
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
