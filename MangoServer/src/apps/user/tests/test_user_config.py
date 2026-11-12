from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from src.apps.user.api.views.user import UserViews
from src.apps.user.exceptions import UserError
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.schemas.preferences import InterfacePreferences
from src.apps.user.services.preferences.user_config import UserConfigService


class UserConfigTests(SimpleTestCase):
    def setUp(self):
        self.rows = {}
        for target in ('src.apps.user.services.preferences.user_config.transaction.atomic',
                       'src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names'):
            mock = patch(target, return_value={} if target.endswith('get_environment_display_names') else MagicMock())
            mock.start()
            self.addCleanup(mock.stop)
        objects = patch('src.apps.user.services.preferences.user_config.User.objects')
        self.objects = objects.start()
        self.addCleanup(objects.stop)
        self.objects.select_for_update.return_value.get.side_effect = lambda pk: self.rows[pk]

    def user(self, config=None, user_id=4):
        user = SimpleNamespace(id=user_id, config=deepcopy(config if config is not None else []),
                               save=MagicMock(), update_user_id=None)
        self.rows[user_id] = user
        return user

    def test_read_all_and_exact_key_share_flat_records_without_database_writes(self):
        user = self.user([UserConfigService._entry('selected_environment', 0)])
        self.assertEqual(UserConfigService.read(user)[0]['key'], 'selected_environment')
        self.assertEqual(UserConfigService.read(user, 'selected_environment')['value'], 0)
        self.assertEqual(UserConfigService.value(user, 'selected_environment'), 0)
        self.assertIsNone(UserConfigService.read(user, 'missing'))
        self.objects.select_for_update.assert_not_called()
        user.save.assert_not_called()

    def test_missing_environment_config_remains_unselected_without_model_field(self):
        user = self.user({})
        self.assertEqual(UserConfigService.read(user), [])
        self.assertIsNone(UserConfigService.selected_environment(user))
        user.save.assert_not_called()

    def test_uniform_update_merges_items_and_uses_identical_audit_fields(self):
        current = self.user([UserConfigService._entry('interface', InterfacePreferences(
            themePreset='royal-purple', actionBar={'isShowSearch': False}).model_dump()),
            UserConfigService._entry('custom.readonly', {'keep': True})])
        stale = SimpleNamespace(id=4, config=[])
        result = UserConfigService.update(stale, [{'key': 'interface', 'value': {'sideWidth': 220}},
                                                  {'key': 'selected_environment', 'value': 0}])
        self.assertIsInstance(current.config, list)
        self.assertEqual({item['key'] for item in result}, {'interface', 'selected_environment', 'custom.readonly'})
        settings = UserConfigService.value(stale, 'interface')
        self.assertEqual(settings['sideWidth'], 220)
        self.assertEqual(settings['themePreset'], 'royal-purple')
        self.assertFalse(settings['actionBar']['isShowSearch'])
        self.assertEqual(UserConfigService.value(stale, 'custom.readonly'), {'keep': True})
        current.save.assert_called_once_with(update_fields=['config', 'update_user', 'update_time'])
        self.assertEqual(current.update_user_id, 4)
        self.assertTrue(all('updated_at' in item and 'name' in item for item in result))

    def test_nested_partial_update_preserves_other_switches_and_density_anchors(self):
        user = self.user()
        UserConfigService.update(user, [{'key': 'interface', 'value': {'autoScale2k': 1.3,
            'autoScale4k': 1.6, 'actionBar': {'isShowSearch': False, 'isShowMessage': False}}}])
        UserConfigService.update(user, [{'key': 'interface', 'value': {'autoScale2k': 1.5,
            'actionBar': {'isShowSearch': True}}}])
        value = UserConfigService.value(user, 'interface')
        self.assertEqual(value['autoScale4k'], 1.6)
        self.assertTrue(value['actionBar']['isShowSearch'])
        self.assertFalse(value['actionBar']['isShowMessage'])

    def test_invalid_batches_never_partially_save_or_accept_metadata_or_other_user_id(self):
        user = self.user()
        cases = [[], {}, [{'key': 'unknown', 'value': 1}],
                 [{'key': 'selected_environment', 'value': True}],
                 [{'key': 'selected_environment', 'value': 99}],
                 [{'key': 'interface', 'value': {'sideWidth': '200'}}],
                 [{'key': 'interface', 'value': {'sideWidth': 200}, 'name': 'Untrusted'}],
                 [{'key': 'interface', 'value': {'id': 9}}],
                 [{'key': 'interface', 'value': {'autoScale2k': 1.5, 'autoScale4k': 1.1}}],
                 [{'key': 'interface', 'value': {'autoScale4k': float('nan')}}],
                 [{'key': 'selected_environment', 'value': 0}, {'key': 'interface', 'value': {'sideWidth': 999}}],
                 [{'key': 'selected_environment', 'value': 0}, {'key': 'selected_environment', 'value': 1}]]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(UserError):
                UserConfigService.update(user, value)
        user.save.assert_not_called()
        self.assertEqual(user.config, [])

    def test_clear_keeps_uniform_metadata_and_leaves_environment_unselected(self):
        user = self.user([UserConfigService._entry('selected_environment', 1)])
        self.assertEqual(UserConfigService.clear(user, key='selected_environment'), 1)
        self.assertIsNone(UserConfigService.selected_environment(user))
        self.assertIsNone(UserConfigService.read(user, 'selected_environment')['value'])
        self.assertEqual(UserConfigService.clear(user, key='selected_environment'), 0)
        self.assertEqual(UserConfigService.clear(user, key='missing'), 0)

    def test_clear_ignores_legacy_clearable_metadata(self):
        user = self.user([UserConfigService._entry('custom.setting', {'keep': True}, clearable=False)])
        self.assertEqual(UserConfigService.clear(user, key='custom.setting'), 1)
        self.assertIsNone(UserConfigService.read(user, 'custom.setting')['value'])
        self.assertEqual(UserConfigService.clear(user, key='custom.setting'), 0)

    def test_old_json_is_read_as_flat_items_and_converted_only_on_explicit_write(self):
        old = {'unrelated': {'keep': True}, 'personal_cache': {'preferences': {'items': {
            'selected_environment': {'value': '0', 'title': '环境', 'value_type': 'environment'}}}}}
        user = self.user(old)
        self.assertEqual(UserConfigService.selected_environment(user), 0)
        self.assertEqual(user.config, old)
        user.save.assert_not_called()
        UserConfigService.update(user, [{'key': 'interface', 'value': {'sideWidth': 230}}])
        self.assertIsInstance(user.config, list)
        self.assertEqual(UserConfigService.value(user, 'unrelated'), {'keep': True})
        self.assertEqual(UserConfigService.selected_environment(user), 0)

    def test_invalid_legacy_values_are_unselected_without_blocking_other_config(self):
        for value in (99, 'missing', [], {}, True):
            with self.subTest(value=value):
                user = self.user({'personal_cache': {'preferences': {'items': {
                    'selected_environment': {'value': value, 'value_type': 'environment'}}}}})
                self.assertIsNone(UserConfigService.selected_environment(user))
                user.save.assert_not_called()

    def test_malformed_historical_groups_do_not_block_read_or_update(self):
        for source in ({'personal_cache': []}, {'personal_cache': {'broken': True}},
                       {'personal_cache': {'broken': {'items': []}}},
                       {'personal_cache': {'preferences': {'items': {'broken': False}}}}):
            user = self.user(source)
            self.assertEqual(UserConfigService.read(user), [])
            user.save.assert_not_called()
            UserConfigService.update(user, [{'key': 'interface', 'value': {'sideWidth': 220}}])
            self.assertEqual(UserConfigService.interface_preferences(user)['sideWidth'], 220)

    def test_route_permissions_and_retired_routes(self):
        view = resolve('/api/user/info/config').func.cls()
        for method, action in [('get', 'get_config'), ('put', 'update_config'), ('delete', 'clear_config')]:
            view.action = action
            request = SimpleNamespace(method=method.upper(), user=None)
            self.assertFalse(MenuActionPermission().has_permission(request, view))
            request.user = SimpleNamespace(user_obj=SimpleNamespace(id=4, is_super_admin=False))
            self.assertTrue(MenuActionPermission().has_permission(request, view))
        for path in ('/api/user/info/cache', '/api/user/info/environment'):
            with self.assertRaises(Resolver404): resolve(path)

    def test_views_use_authenticated_user_and_delete_reads_query_key(self):
        user = self.user()
        request = SimpleNamespace(user=SimpleNamespace(user_obj=user), data=[], query_params=QueryDict('key=interface'))
        with patch.object(UserConfigService, 'read', return_value=[]) as read:
            UserViews().get_config(request)
        read.assert_called_once_with(user, key='interface')
        request.data = [{'key': 'interface', 'value': {'sideWidth': 200}}]
        with patch.object(UserConfigService, 'update', return_value=[]) as update:
            self.assertEqual(UserViews().update_config(request).data['code'], 200)
        update.assert_called_once_with(user, request.data)
        request.data = {}
        with patch.object(UserConfigService, 'clear', return_value=1) as clear:
            self.assertEqual(UserViews().clear_config(request).data['data']['count'], 1)
        clear.assert_called_once_with(user, key='interface')
