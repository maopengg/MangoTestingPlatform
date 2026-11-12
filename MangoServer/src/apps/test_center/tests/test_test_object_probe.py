import socket
from concurrent.futures import Future, TimeoutError as FutureTimeout
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.urls import resolve
from mangotools.enums import DriveTypeEnum

from src.apps.test_center.api.serializers.test_object import TestObjectProbeSerializer, TestObjectSerializersC
from src.apps.test_center.api.views.test_object import TestObjectViews
from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.environment.test_object_probe import TestObjectProbeService as Probe
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class TestObjectProbeTests(SimpleTestCase):
    def obj(self, auto_type=AutoTypeEnum.API.value, ui_type=DriveTypeEnum.WEB.value, value='https://api.example.com/path'):
        return SimpleNamespace(id=7, value=value, target_config={}, auto_type=auto_type, project_product_id=9,
                               project_product=SimpleNamespace(ui_client_type=ui_type))

    def test_product_client_type_and_network_format_rules(self):
        for client in DriveTypeEnum:
            for auto_type in AutoTypeEnum:
                obj = self.obj(auto_type.value, client.value)
                expected = auto_type != AutoTypeEnum.UI or client == DriveTypeEnum.WEB
                self.assertEqual(bool(Probe.network_options(obj)), expected)
        for value in ('com.example.app', '/opt/app', r'C:\app.exe', 'file:///tmp/a', 'https://user:secret@example.com',
                      'https://api.example.com:0', 'https://api.example.com:99999', 'https://[broken'):
            self.assertEqual(Probe.network_options(self.obj(value=value)), [])
        self.assertEqual(Probe.network_options(self.obj(auto_type=99)), [])

    def test_mapping_options_are_static_unique_and_do_not_resolve_variables(self):
        obj = self.obj(value='')
        obj.target_config = {'default': 'https://api.example.com', 'selector': 'tenant', 'mapping': {
            'one': 'https://api.example.com', 'two': 'https://other.example.com:8443', 'app': 'com.example.app'}}
        options = Probe.network_options(obj)
        self.assertEqual([x['value'] for x in options], ['https://api.example.com', 'https://other.example.com:8443'])
        self.assertEqual(options[1]['label'], '条件值：two')
        self.assertEqual(TestObjectSerializersC().get_network_test_addresses(obj), options)

    def test_serializer_requires_saved_id(self):
        for data in ({}, {'id': 0}, {'id': 1, 'address': 'a' * 1025}):
            self.assertFalse(TestObjectProbeSerializer(data=data).is_valid())

    def test_permission_and_scope_checked_before_network(self):
        user = SimpleNamespace(id=1)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'config.test_object'}), \
                patch('src.apps.test_center.services.environment.test_object_probe.TestObject.objects') as objects:
            for identity in (user, None):
                with self.assertRaises(TestCenterError):
                    Probe.test(7, '', identity)
            objects.select_related.assert_not_called()
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=False), \
                patch('src.apps.test_center.services.environment.test_object_probe.TestObject.objects') as objects, \
                patch.object(Probe, '_probe') as network:
            objects.select_related.return_value.filter.return_value.first.return_value = self.obj()
            with self.assertRaises(TestCenterError):
                Probe.test(7, '', user)
            network.assert_not_called()

    def test_only_saved_and_applicable_addresses_can_be_tested(self):
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=True), \
                patch('src.apps.test_center.services.environment.test_object_probe.TestObject.objects') as objects, \
                patch.object(Probe, '_probe') as network:
            obj = self.obj()
            objects.select_related.return_value.filter.return_value.first.return_value = obj
            with self.assertRaises(TestCenterError):
                Probe.test(7, 'https://unconfigured.example.com', SimpleNamespace(id=1))
            obj.auto_type = AutoTypeEnum.UI.value
            obj.project_product.ui_client_type = DriveTypeEnum.ANDROID.value
            with self.assertRaises(TestCenterError):
                Probe.test(7, obj.value, SimpleNamespace(id=1))
            network.assert_not_called()

    def test_request_result_and_busy_timeout_are_bounded(self):
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=True), \
                patch('src.apps.test_center.services.environment.test_object_probe.TestObject.objects') as objects, \
                patch.object(Probe, '_slots') as slots, patch.object(Probe, '_executor') as executor:
            objects.select_related.return_value.filter.return_value.first.return_value = self.obj()
            slots.acquire.return_value = True
            future = Future()
            future.set_result({'connected': True, 'resolved_ips': ['10.0.0.5'], 'message': 'ok'})
            executor.submit.return_value = future
            result = Probe.test(7, '', SimpleNamespace(id=1))
            self.assertTrue(result['connected'])
            self.assertEqual(result['port'], 443)
            slots.release.assert_called_once()
            executor.submit.assert_called_once_with(Probe._probe, 'api.example.com', 443)
            slots.acquire.return_value = False
            self.assertIn('稍后重试', Probe.test(7, '', SimpleNamespace(id=1))['message'])
            slots.acquire.return_value = True
            executor.submit.return_value = MagicMock()
            executor.submit.return_value.result.side_effect = FutureTimeout
            self.assertIn('超时', Probe.test(7, '', SimpleNamespace(id=1))['message'])
            executor.submit.return_value.result.assert_called_once_with(timeout=5)

    def test_special_addresses_blocked_but_internal_network_allowed(self):
        for ip in ('127.0.0.1', '::1', '169.254.169.254', '100.100.100.200', 'fd00:ec2::254',
                   '0.0.0.0', '224.0.0.1', '::ffff:127.0.0.1'):
            self.assertFalse(Probe._safe_ip(ip), ip)
        self.assertTrue(Probe._safe_ip('10.0.0.5'))
        with patch('src.apps.test_center.services.environment.test_object_probe.socket.getaddrinfo', return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('169.254.169.254', 80))]), \
                patch('src.apps.test_center.services.environment.test_object_probe.socket.socket') as sock:
            self.assertIn('不允许', Probe._probe('api.example.com', 80)['message'])
            sock.assert_not_called()

    def test_dns_and_connection_failure_and_pinned_success(self):
        with patch('src.apps.test_center.services.environment.test_object_probe.socket.getaddrinfo', side_effect=socket.gaierror):
            self.assertIn('解析失败', Probe._probe('api.example.com', 443)['message'])
        entry = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.5', 443))
        with patch('src.apps.test_center.services.environment.test_object_probe.socket.getaddrinfo', return_value=[entry]), \
                patch('src.apps.test_center.services.environment.test_object_probe.socket.socket') as sock:
            result = Probe._probe('api.example.com', 443)
            self.assertTrue(result['connected'])
            sock.return_value.__enter__.return_value.connect.assert_called_once_with(('10.0.0.5', 443))
            sock.return_value.__enter__.return_value.connect.side_effect = ConnectionRefusedError
            self.assertIn('端口连接失败', Probe._probe('api.example.com', 443)['message'])

    def test_http_permission_registration_and_guest_boundary(self):
        self.assertEqual(resolve('/api/system/test/object/test').func.actions['post'], 'test_connection')
        self.assertIn('config.test_object:read', PermissionMenuService.guest_permission_keys())
        self.assertNotIn('config.test_object:change', PermissionMenuService.guest_permission_keys())
        request = SimpleNamespace(method='POST', path='/api/system/test/object/test', data={'id': 7},
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=1, role_id=None)))
        view = TestObjectViews()
        view.action = 'test_connection'
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False):
            self.assertTrue(MenuActionPermission().has_permission(request, view))

    def test_guest_probe_preserves_scope_and_never_mutates_saved_target(self):
        user = SimpleNamespace(id=1, role_id=None)
        future = Future()
        future.set_result({'connected': True, 'message': 'ok'})
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=True) as scope, \
                patch('src.apps.test_center.services.environment.test_object_probe.TestObject.objects') as objects, \
                patch.object(Probe, '_executor') as executor:
            objects.select_related.return_value.filter.return_value.first.return_value = self.obj()
            executor.submit.return_value = future
            self.assertTrue(Probe.test(7, '', user)['connected'])
            executor.submit.assert_called_once_with(Probe._probe, 'api.example.com', 443)
            objects.create.assert_not_called()
            objects.update.assert_not_called()
            objects.select_related.return_value.filter.return_value.update.assert_not_called()
            scope.return_value = False
            executor.submit.reset_mock()
            with self.assertRaises(TestCenterError):
                Probe.test(7, '', user)
            executor.submit.assert_not_called()
