from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from src.apps.user.middleware.user_logs import UserLogsMiddleWare
from src.apps.user.services.permission import PermissionMenuService, RoleMenuPermission


class GetLogPerformanceTests(SimpleTestCase):
    def test_envelope_discards_body_before_redaction_without_changing_logged_metadata(self):
        class UnreadableBody(dict):
            def items(self):
                raise AssertionError('日志不应遍历已丢弃的响应正文')

        response = SimpleNamespace(data={'code': 200, 'msg': 'ok', 'data': UnreadableBody(payload='large'),
                                         'meta': {'authorization': 'example-secret', 'total': 10000}})
        middleware = UserLogsMiddleWare(lambda request: None)
        self.assertEqual(middleware._capture_response_data(response),
                         '{"code": 200, "msg": "ok", "meta": {"authorization": "***", "total": 10000}}')
        self.assertEqual(response.data['meta']['authorization'], 'example-secret')
        self.assertIn('data', response.data)

    def test_unwrapped_response_keeps_redaction_and_length_limit(self):
        middleware = UserLogsMiddleWare(lambda request: None)
        original = {'token': 'example-secret', 'text': 'x' * 3000}
        response = SimpleNamespace(data=original)
        value = middleware._capture_response_data(response)
        self.assertEqual(len(value), 2000)
        self.assertIn('"token": "***"', value)
        self.assertNotIn('example-secret', value)
        self.assertEqual(original['token'], 'example-secret')

    def test_get_submits_an_audit_snapshot_without_creating_a_per_request_thread(self):
        middleware = UserLogsMiddleWare(lambda request: None)
        response = SimpleNamespace(status_code=200, data={'code': 200, 'msg': 'ok', 'data': []})
        with patch('src.apps.user.middleware.user_logs.UserLogService.submit') as submit:
            self.assertIs(middleware.process_response(RequestFactory().get('/api/example'), response), response)
        submit.assert_called_once()
        self.assertEqual(submit.call_args.args[0]['method'], 'GET')


class PermissionCatalogPerformanceTests(SimpleTestCase):
    def setUp(self):
        self.clear_cache()
        self.addCleanup(self.clear_cache)

    @staticmethod
    def clear_cache():
        PermissionMenuService._static_permission_tree.cache_clear()
        PermissionMenuService._static_permission_keys.cache_clear()

    def test_static_tree_is_built_once_and_public_results_are_isolated(self):
        tree = [{'menuUrl': '/example', 'permissionKey': 'example', 'children': []}]
        with patch('src.apps.user.services.permission.ad_routes', return_value=deepcopy(tree)) as factory:
            first = PermissionMenuService.permission_tree()
            first[0]['menuName'] = 'changed'
            first[0]['actions'].clear()
            second = PermissionMenuService.permission_tree()
            keys = PermissionMenuService.all_permission_keys()
            keys.clear()
            self.assertNotIn('menuName', second[0])
            self.assertTrue(second[0]['actions'])
            self.assertIn('example:read', PermissionMenuService.all_permission_keys())
            factory.assert_called_once()

    def test_environment_has_an_independent_static_snapshot(self):
        with patch('src.apps.user.services.permission.ad_routes', return_value=[]) as factory:
            with patch.dict('os.environ', {'DJANGO_ENV': 'dev'}):
                PermissionMenuService.permission_tree()
            with patch.dict('os.environ', {'DJANGO_ENV': 'test'}):
                PermissionMenuService.permission_tree()
                PermissionMenuService.permission_tree()
            self.assertEqual(factory.call_count, 2)

    def test_role_grants_are_not_cached_across_checks(self):
        user = SimpleNamespace(is_super_admin=False, username='reader@example.com', role_id=7,
                               role=SimpleNamespace(name='普通角色'))
        with patch.object(RoleMenuPermission.objects, 'filter') as stored:
            stored.return_value.values_list.side_effect = [['api.info:read'], ['api.info:change']]
            first = PermissionMenuService.permission_keys_for_user(user)
            second = PermissionMenuService.permission_keys_for_user(user)
            self.assertIn('api.info:read', first)
            self.assertNotIn('api.info:change', first)
            self.assertNotIn('api.info:read', second)
            self.assertIn('api.info:change', second)
            self.assertEqual(stored.call_count, 2)
