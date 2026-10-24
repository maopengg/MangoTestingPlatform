import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mangotools.enums import CacheValueTypeEnum

from src.consumer.tools import Tools
from src.enums.tools_enum import CacheKeyEnum
from src.tk_pages.pages.login import LoginPage
from src.settings import settings
from src.tools.set_config import SetConfig


class OpenStatusCacheTest(unittest.TestCase):

    def setUp(self):
        self.original_is_open = settings.IS_OPEN

    def tearDown(self):
        settings.IS_OPEN = self.original_is_open

    def test_open_status_uses_boolean_cache_type(self):
        self.assertEqual(
            CacheKeyEnum.obj()[CacheKeyEnum.IS_OPEN.value],
            CacheValueTypeEnum.BOOL,
        )

    def test_set_open_status_updates_cache_and_runtime(self):
        with patch.object(SetConfig, 'set_is_open') as set_is_open:
            result = SetConfig.set_open_status(False)

        self.assertFalse(result)
        self.assertFalse(settings.IS_OPEN)
        set_is_open.assert_called_once_with(False)

    def test_restore_runtime_settings_keeps_cached_false(self):
        with patch.object(SetConfig, 'get_is_open', return_value=False):
            SetConfig.restore_runtime_settings()

        self.assertFalse(settings.IS_OPEN)

    def test_restore_runtime_settings_defaults_to_true_without_cache(self):
        with patch.object(SetConfig, 'get_is_open', return_value=None):
            SetConfig.restore_runtime_settings()

        self.assertTrue(settings.IS_OPEN)

    def test_remote_runtime_config_persists_open_status(self):
        with patch.object(SetConfig, 'set_open_status') as set_open_status:
            Tools._apply_actuator_config({'runtime': {'is_open': False}})

        set_open_status.assert_called_once_with(False)

    def test_get_actuator_config_returns_snapshot_for_unified_task_result(self):
        config = {'runtime': {'is_open': True}}
        with patch.object(Tools, '_collect_actuator_config', return_value=config), \
                patch.object(SetConfig, 'get_username', return_value='executor-user'), \
                patch('src.consumer.tools.socket_conn.async_send', new_callable=AsyncMock) as send:
            result = asyncio.run(Tools.t_get_actuator_config({'request_id': 'request-1'}))

        self.assertEqual(result, {
            'request_id': 'request-1',
            'username': 'executor-user',
            'status': True,
            'config': config,
        })
        self.assertEqual(send.await_args.kwargs['func_args'], result)

    def test_update_actuator_config_returns_save_result_for_unified_task(self):
        config = {'runtime': {'debug': True}}
        with patch.object(Tools, '_apply_actuator_config') as apply_config, \
                patch.object(Tools, '_collect_actuator_config', return_value=config), \
                patch.object(SetConfig, 'get_username', return_value='executor-user'), \
                patch('src.consumer.tools.socket_conn.async_send', new_callable=AsyncMock) as send:
            result = asyncio.run(Tools.t_update_actuator_config({
                'request_id': 'request-2',
                'config': config,
            }))

        apply_config.assert_called_once_with(config)
        self.assertTrue(result['status'])
        self.assertEqual(result['config'], config)
        self.assertEqual(send.await_args.kwargs['func_args'], result)

    def test_web_headers_default_does_not_override_cached_false(self):
        with patch.object(SetConfig, 'get_web_headers', return_value=False), \
                patch.object(SetConfig, 'set_web_headers') as set_web_headers:
            result = SetConfig.ensure_web_headers_default(True)

        self.assertFalse(result)
        set_web_headers.assert_not_called()

    def test_web_headers_default_is_only_written_when_cache_is_missing(self):
        with patch.object(SetConfig, 'get_web_headers', return_value=None), \
                patch.object(SetConfig, 'set_web_headers') as set_web_headers:
            result = SetConfig.ensure_web_headers_default(True)

        self.assertTrue(result)
        set_web_headers.assert_called_once_with(True)

class LoginCredentialCacheTest(unittest.TestCase):

    def setUp(self):
        self.original_runtime_password = SetConfig._runtime_password

    def tearDown(self):
        SetConfig._runtime_password = self.original_runtime_password

    def test_remembered_login_controls_password_prefill(self):
        with patch.object(SetConfig, 'get_remember_username', return_value='maopeng'), \
                patch.object(SetConfig, 'get_username', return_value='fallback'), \
                patch.object(SetConfig, 'get_remember_password', return_value='secret'):
            result = SetConfig.get_remembered_login()

        self.assertEqual(result, ('maopeng', 'secret', True))

    def test_unchecked_password_is_runtime_only(self):
        with patch.object(SetConfig, 'set_username'), \
                patch.object(SetConfig, 'set_remember_username'), \
                patch.object(SetConfig, 'set_password') as set_password, \
                patch.object(SetConfig, 'set_remember_password') as set_remember_password, \
                patch.object(SetConfig, 'delete_cache') as delete_cache:
            SetConfig.save_login_credentials('maopeng', 'secret', False)

        self.assertEqual(SetConfig.get_login_password(), 'secret')
        set_password.assert_not_called()
        set_remember_password.assert_not_called()
        self.assertEqual(
            [call.args[0] for call in delete_cache.call_args_list],
            [CacheKeyEnum.PASSWORD.value, CacheKeyEnum.REMEMBER_PASSWORD.value],
        )

    def test_checked_password_is_persisted(self):
        with patch.object(SetConfig, 'set_username'), \
                patch.object(SetConfig, 'set_remember_username'), \
                patch.object(SetConfig, 'set_password') as set_password, \
                patch.object(SetConfig, 'set_remember_password') as set_remember_password, \
                patch.object(SetConfig, 'delete_cache') as delete_cache:
            SetConfig.save_login_credentials('maopeng', 'secret', True)

        set_password.assert_called_once_with('secret')
        set_remember_password.assert_called_once_with('secret')
        delete_cache.assert_not_called()

    def test_login_in_progress_disables_repeated_submission(self):
        login_button = SimpleNamespace(
            configure=lambda **values: [setattr(login_button, key, value) for key, value in values.items()],
        )
        login = SimpleNamespace(_login_in_progress=False, login_button=login_button)

        LoginPage._set_login_in_progress(login, True)

        self.assertTrue(login._login_in_progress)
        self.assertEqual(login_button.state, 'disabled')
        self.assertEqual(login_button.text, '登录中...')


if __name__ == '__main__':
    unittest.main()
