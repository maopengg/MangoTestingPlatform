from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.hashers import check_password
from django.test import SimpleTestCase

from src.apps.user.api.serializers.user import (
    UserSerializers,
    UserSerializersC,
)
from src.apps.user.api.views.user import (
    LoginViews,
    UserViews,
    double_md5,
)
from src.apps.user.exceptions import USER_CREDENTIAL_USER_NOT_ALLOWED, UserError
from src.apps.user.services.credential import UserCredentialService
from src.apps.user.services.password import encode_plain_password, verify_password_digest


class UserSecurityTests(SimpleTestCase):
    def test_deprecated_mailbox_is_not_exposed_by_user_serializers(self):
        self.assertNotIn("mailbox", UserSerializers().fields)
        self.assertNotIn("mailbox", UserSerializersC().fields)

    def test_user_edit_rejects_legacy_login_name(self):
        serializer = UserSerializers()

        with self.assertRaisesRegex(UserError, "正确的邮箱地址"):
            serializer.validate_username("legacy-user")

    @patch("src.apps.user.api.serializers.user.UserCredentialService.ensure_email_available")
    def test_user_edit_normalizes_email_and_checks_uniqueness(self, ensure_email_available):
        serializer = UserSerializers(instance=SimpleNamespace(id=2))

        email = serializer.validate_username(" User@Example.com ")

        self.assertEqual(email, "user@example.com")
        ensure_email_available.assert_called_once_with("user@example.com", exclude_user_id=2)

    @patch("src.apps.user.services.credential.SystemConfigService.get", return_value="")
    def test_missing_mail_config_points_to_system_settings(self, _get_config):
        with self.assertRaisesRegex(UserError, "系统运维 → 配置管理 → 邮箱配置"):
            UserCredentialService._mail_config()

    def test_generated_password_meets_strength_requirements(self):
        password = UserCredentialService.generate_password()

        self.assertEqual(len(password), UserCredentialService.PASSWORD_LENGTH)
        self.assertIsNone(LoginViews._validate_register_password("user@example.com", "用户", password))

    @patch("src.apps.user.api.views.user.transaction.atomic", return_value=nullcontext())
    @patch("src.apps.user.api.views.user.UserCredentialService.send_password")
    @patch("src.apps.user.api.views.user.UserCredentialService.ensure_email_available")
    @patch("src.apps.user.api.views.user.UserCredentialService.generate_password", return_value="RandomPassword1!")
    @patch("src.apps.user.api.views.user.User.unique_api_key", return_value="mango_new_key")
    @patch(
        "src.apps.user.api.views.user.PermissionMenuService.is_effective_super_admin",
        return_value=True,
    )
    @patch("src.apps.user.api.views.user.UserViews.serializer")
    @patch("src.apps.user.api.views.user.User.objects.create")
    @patch("src.apps.user.api.views.user.User.objects.filter")
    @patch("src.apps.user.api.views.user.Role.objects.filter")
    def test_admin_registration_accepts_role_and_super_admin(
            self,
            filter_roles,
            filter_users,
            create_user,
            serializer,
            _is_effective_super_admin,
            _unique_api_key,
            _generate_password,
            _ensure_email_available,
            send_password,
            _atomic,
    ):
        operator = SimpleNamespace(id=1)
        role = SimpleNamespace(id=3)
        user = SimpleNamespace(id=2)
        filter_roles.return_value.first.return_value = role
        filter_users.return_value.exists.return_value = False
        create_user.return_value = user
        serializer.return_value.data = {"id": user.id}
        request = SimpleNamespace(
            data={
                "name": "目标用户",
                "email": "Target@Example.com",
                "role": role.id,
                "is_super_admin": True,
            },
            user=SimpleNamespace(user_obj=operator),
        )

        response = UserViews().register_user(request)

        self.assertEqual(response.data["code"], 200)
        create_user.assert_called_once()
        create_kwargs = create_user.call_args.kwargs
        self.assertEqual(create_kwargs["username"], "target@example.com")
        self.assertEqual(create_kwargs["role"], role)
        self.assertTrue(create_kwargs["is_super_admin"])
        self.assertEqual(create_kwargs["update_user"], operator)
        send_password.assert_called_once_with(
            email="target@example.com",
            name="目标用户",
            password="RandomPassword1!",
            action="账号注册",
        )

    @patch(
        "src.apps.user.api.views.user.PermissionMenuService.is_effective_super_admin",
        return_value=False,
    )
    @patch("src.apps.user.api.views.user.UserCredentialService.ensure_email_available")
    @patch("src.apps.user.api.views.user.User.objects.filter")
    @patch("src.apps.user.api.views.user.Role.objects.filter")
    def test_admin_registration_rejects_super_admin_privilege_escalation(
            self,
            filter_roles,
            filter_users,
            _ensure_email_available,
            _is_effective_super_admin,
    ):
        filter_roles.return_value.first.return_value = SimpleNamespace(id=3)
        filter_users.return_value.exists.return_value = False
        request = SimpleNamespace(
            data={
                "name": "目标用户",
                "email": "target@example.com",
                "role": 3,
                "is_super_admin": True,
            },
            user=SimpleNamespace(user_obj=SimpleNamespace(id=1)),
        )

        response = UserViews().register_user(request)

        self.assertEqual(response.data["code"], 300)
        self.assertIn("只有超级管理员", response.data["msg"])

    @patch("src.apps.user.api.views.user.transaction.atomic", return_value=nullcontext())
    @patch("src.apps.user.api.views.user.UserCredentialService.send_password")
    @patch("src.apps.user.api.views.user.UserCredentialService.ensure_email_available")
    @patch("src.apps.user.api.views.user.UserCredentialService.generate_password", return_value="RandomPassword1!")
    @patch("src.apps.user.api.views.user.User.unique_api_key", return_value="mango_new_key")
    @patch("src.apps.user.api.views.user.UserViews.serializer")
    @patch("src.apps.user.api.views.user.User.objects.create")
    @patch("src.apps.user.api.views.user.User.objects.filter")
    @patch("src.apps.user.api.views.user.PermissionMenuService.default_role")
    def test_admin_registration_defaults_to_guest_without_super_admin(
            self,
            default_role,
            filter_users,
            create_user,
            serializer,
            _unique_api_key,
            _generate_password,
            _ensure_email_available,
            _send_password,
            _atomic,
    ):
        guest_role = SimpleNamespace(id=1)
        user = SimpleNamespace(id=2)
        default_role.return_value = guest_role
        filter_users.return_value.exists.return_value = False
        create_user.return_value = user
        serializer.return_value.data = {"id": user.id}
        request = SimpleNamespace(
            data={"name": "目标用户", "email": "target@example.com", "role": None},
            user=SimpleNamespace(user_obj=SimpleNamespace(id=1)),
        )

        response = UserViews().register_user(request)

        self.assertEqual(response.data["code"], 200)
        create_kwargs = create_user.call_args.kwargs
        self.assertEqual(create_kwargs["role"], guest_role)
        self.assertFalse(create_kwargs["is_super_admin"])

    @patch(
        'src.apps.system.services.system_config.SystemConfigService.get_registration_config',
        return_value={'allow_registration': False, 'disabled_message': '注册功能已关闭'},
    )
    def test_register_endpoint_honors_backend_switch(self, _config):
        request = SimpleNamespace(data={})

        with patch.object(LoginViews, '_is_super_admin_registration', return_value=False):
            response = LoginViews().register(request)

        self.assertEqual(response.data["code"], 300)
        self.assertEqual(response.data["msg"], "注册功能已关闭")

    @patch(
        'src.apps.system.services.system_config.SystemConfigService.get_registration_config',
        return_value={'allow_registration': False, 'disabled_message': '注册功能已关闭'},
    )
    def test_super_admin_can_bypass_public_registration_switch(self, _config):
        request = SimpleNamespace(data={})

        with patch.object(LoginViews, '_is_super_admin_registration', return_value=True):
            response = LoginViews().register(request)

        self.assertEqual(response.data["code"], USER_CREDENTIAL_USER_NOT_ALLOWED.code)
        self.assertIn('不允许为空', response.data["msg"])

    def test_change_password_ignores_submitted_user_id(self):
        current_user = SimpleNamespace(
            id=1,
            username="user@example.com",
            name="用户",
            password=encode_plain_password("OldPassword1!"),
            save=MagicMock(),
        )
        request = SimpleNamespace(
            data={
                "id": 999,
                "password": "OldPassword1!",
                "new_password": "NewPassword2!",
                "confirm_password": "NewPassword2!",
            },
            user=SimpleNamespace(user_obj=current_user),
        )

        with patch("src.apps.user.api.views.user.User.objects.get") as get_user:
            response = UserViews().put_password(request)

        get_user.assert_not_called()
        self.assertEqual(response.data["code"], 200)
        self.assertTrue(check_password(double_md5("NewPassword2!"), current_user.password))
        current_user.save.assert_called_once_with(update_fields=["password"])

    @patch("src.apps.user.api.views.user.UserCredentialService.ensure_email_available")
    def test_legacy_user_changes_to_email_login_when_updating_password(self, ensure_email_available):
        current_user = SimpleNamespace(
            id=1,
            username="legacy-user",
            name="历史用户",
            password=encode_plain_password("OldPassword1!"),
            save=MagicMock(),
        )
        request = SimpleNamespace(
            data={
                "password": "OldPassword1!",
                "new_password": "NewPassword2!",
                "confirm_password": "NewPassword2!",
                "email": "User@Example.com",
            },
            user=SimpleNamespace(user_obj=current_user),
        )

        response = UserViews().put_password(request)

        self.assertEqual(response.data["code"], 200)
        self.assertEqual(current_user.username, "user@example.com")
        ensure_email_available.assert_called_once_with("user@example.com", exclude_user_id=1)
        current_user.save.assert_called_once_with(update_fields=["password", "username"])

    def test_legacy_digest_is_upgraded_after_successful_login(self):
        password_digest = double_md5("OldPassword1!")

        valid, upgraded_password = verify_password_digest(password_digest, password_digest)

        self.assertTrue(valid)
        self.assertIsNotNone(upgraded_password)
        self.assertNotEqual(upgraded_password, password_digest)
        self.assertTrue(check_password(password_digest, upgraded_password))

    def test_django_hash_cannot_be_replayed_as_login_credential(self):
        password_digest = double_md5("OldPassword1!")
        stored_password = encode_plain_password("OldPassword1!")

        valid, _ = verify_password_digest(stored_password, stored_password)

        self.assertFalse(valid)

    @patch("src.apps.user.api.views.user.transaction.atomic", return_value=nullcontext())
    @patch("src.apps.user.api.views.user.UserCredentialService.send_password")
    @patch("src.apps.user.api.views.user.UserCredentialService.generate_password", return_value="RandomPassword1!")
    @patch("src.apps.user.api.views.user.User.objects.select_for_update")
    def test_admin_reset_generates_password_and_sends_email(
            self, select_for_update, generate_password, send_password, _atomic
    ):
        operator = SimpleNamespace(id=1)
        target_user = SimpleNamespace(
            id=2,
            username="target@example.com",
            name="目标用户",
            password="",
            update_user=None,
            save=MagicMock(),
        )
        select_for_update.return_value.filter.return_value.first.return_value = target_user
        request = SimpleNamespace(
            data={"id": target_user.id},
            user=SimpleNamespace(user_obj=operator),
        )

        response = UserViews().reset_password(request)

        self.assertEqual(response.data["code"], 200)
        self.assertTrue(check_password(double_md5("RandomPassword1!"), target_user.password))
        self.assertEqual(target_user.update_user, operator)
        generate_password.assert_called_once_with()
        send_password.assert_called_once_with(
            email="target@example.com",
            name="目标用户",
            password="RandomPassword1!",
            action="密码重置",
        )
        target_user.save.assert_called_once_with(
            update_fields=["password", "update_user", "update_time"]
        )

    @patch("src.apps.user.api.views.user.transaction.atomic", return_value=nullcontext())
    @patch("src.apps.user.api.views.user.User.objects.select_for_update")
    def test_admin_reset_requires_email_login(self, select_for_update, _atomic):
        target_user = SimpleNamespace(
            id=2,
            username="target-user",
            name="目标用户",
            save=MagicMock(),
        )
        select_for_update.return_value.filter.return_value.first.return_value = target_user
        request = SimpleNamespace(
            data={"id": target_user.id},
            user=SimpleNamespace(user_obj=SimpleNamespace(id=1)),
        )

        response = UserViews().reset_password(request)

        self.assertEqual(response.data["code"], 300)
        self.assertIn("邮箱登录", response.data["msg"])
        target_user.save.assert_not_called()

    @patch("src.apps.user.api.views.user.User.unique_api_key", return_value="mango_new_key")
    @patch("src.apps.user.api.views.user.User.objects.filter")
    def test_admin_can_reset_user_api_key(self, filter_users, unique_api_key):
        operator = SimpleNamespace(id=1)
        target_user = SimpleNamespace(
            id=2,
            api_key="mango_old_key",
            update_user=None,
            save=MagicMock(),
        )
        filter_users.return_value.first.return_value = target_user
        request = SimpleNamespace(
            data={"id": target_user.id},
            user=SimpleNamespace(user_obj=operator),
        )

        response = UserViews().reset_user_api_key(request)

        self.assertEqual(response.data["code"], 200)
        self.assertEqual(target_user.api_key, "mango_new_key")
        self.assertEqual(target_user.update_user, operator)
        unique_api_key.assert_called_once_with()
        target_user.save.assert_called_once_with(
            update_fields=["api_key", "update_user", "update_time"]
        )
        self.assertNotIn("mango_new_key", str(response.data))

    @patch("src.apps.user.api.views.user.User.objects.filter")
    def test_admin_reset_user_api_key_rejects_missing_user(self, filter_users):
        filter_users.return_value.first.return_value = None
        request = SimpleNamespace(
            data={"id": 999},
            user=SimpleNamespace(user_obj=SimpleNamespace(id=1)),
        )

        response = UserViews().reset_user_api_key(request)

        self.assertEqual(response.data["code"], 300)
        self.assertIn("不存在", response.data["msg"])

    @patch("src.apps.user.api.views.user.transaction.atomic", return_value=nullcontext())
    @patch("src.apps.user.api.views.user.UserCredentialService.send_password")
    @patch("src.apps.user.api.views.user.UserCredentialService.generate_password", return_value="RandomPassword1!")
    @patch("src.apps.user.api.views.user.User.objects.select_for_update")
    def test_public_email_reset_generates_and_sends_password(
            self, select_for_update, generate_password, send_password, _atomic
    ):
        target_user = SimpleNamespace(
            id=2,
            username="target@example.com",
            name="目标用户",
            password="",
            save=MagicMock(),
        )
        select_for_update.return_value.filter.return_value.first.return_value = target_user

        response = LoginViews().reset_password_by_email(
            SimpleNamespace(data={"email": "Target@Example.com"})
        )

        self.assertEqual(response.data["code"], 200)
        self.assertTrue(check_password(double_md5("RandomPassword1!"), target_user.password))
        select_for_update.return_value.filter.assert_called_once_with(
            username__iexact="target@example.com"
        )
        send_password.assert_called_once_with(
            email="target@example.com",
            name="目标用户",
            password="RandomPassword1!",
            action="密码重置",
        )
