from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate

from src.apps.user.enums.permission import HttpPermissionBoundaryEnum
from src.apps.user.exceptions import USER_CREDENTIAL_USER_BINDING_INVALID, UserError
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.account.account_mutation import UserAccountMutationService
from src.apps.user.services.authorization.http_permission_boundaries import HTTP_PERMISSION_BOUNDARIES
from src.apps.user.services.authorization.permission import PermissionMenuService


class PersonalPasswordResetTests(SimpleTestCase):
    path = '/api/user/info/reset-own-password'

    def call(self, user, data=None):
        request = APIRequestFactory().put(self.path, data or {}, format='json')
        force_authenticate(request, user=SimpleNamespace(user_obj=user))
        return resolve(self.path).func(request)

    def test_account_boundary_is_authenticated_default_not_user_management(self):
        match = resolve(self.path)
        key = (f'{match.func.cls.__module__}.{match.func.cls.__name__}', 'reset_own_password', 'put')
        self.assertEqual(HTTP_PERMISSION_BOUNDARIES[key], HttpPermissionBoundaryEnum.ACCOUNT)
        view = match.func.cls()
        view.action = 'reset_own_password'
        self.assertFalse(MenuActionPermission().has_permission(SimpleNamespace(method='PUT', user=None), view))

    def test_all_logged_in_roles_reset_only_themselves_without_old_password(self):
        for role in ('游客', '普通角色', '管理员'):
            user = SimpleNamespace(id=7, role_id=1, role=SimpleNamespace(name=role))
            with self.subTest(role=role), \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', side_effect=AssertionError('个人入口不查菜单权限')), \
                    patch.object(UserAccountMutationService, 'reset_password', return_value=user) as reset:
                response = self.call(user, {'id': 99, 'user_id': 99, 'email': 'other@example.com'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['code'], 200)
                self.assertIsNone(response.data['data'])
                reset.assert_called_once_with(7, operator=user)

    def test_guest_still_cannot_reset_someone_else_via_admin_endpoint(self):
        user = SimpleNamespace(id=7, role_id=1, role=SimpleNamespace(name='游客'))
        request = APIRequestFactory().put('/api/user/info/reset-password', {'id': 99}, format='json')
        force_authenticate(request, user=SimpleNamespace(user_obj=user))
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(UserAccountMutationService, 'reset_password') as reset:
            response = resolve('/api/user/info/reset-password').func(request)
            self.assertNotEqual(response.data['code'], 200)
            reset.assert_not_called()

    def test_missing_login_email_is_returned_without_exposing_a_password(self):
        user = SimpleNamespace(id=7)
        with patch.object(UserAccountMutationService, 'reset_password',
                          side_effect=UserError(USER_CREDENTIAL_USER_BINDING_INVALID)):
            response = self.call(user)
        self.assertEqual(response.data['code'], USER_CREDENTIAL_USER_BINDING_INVALID.code)
        self.assertIsNone(response.data['data'])
