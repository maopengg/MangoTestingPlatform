from unittest.mock import patch

from django.apps import apps
from django.test import SimpleTestCase

from src.apps.user.models import User
from src.apps.user.services.password import double_md5, verify_password_digest


class DeploymentCredentialsTests(SimpleTestCase):
    def test_new_install_uses_separate_admin_and_guest_credentials(self):
        with patch.dict('os.environ', {
            'MANGO_INITIAL_ADMIN_PASSWORD': 'InitialAdminForTest1!',
            'MANGO_INITIAL_GUEST_PASSWORD': 'InitialGuestForTest2!',
        }), patch.object(User.objects, 'exists', return_value=False), \
                patch.object(User, 'unique_api_key', side_effect=['test-admin-key', 'test-guest-key']), \
                patch.object(User.objects, 'bulk_create') as create:
            apps.get_app_config('auto_user').new_user()
        admin, guest = create.call_args.args[0]
        self.assertTrue(admin.is_super_admin)
        self.assertFalse(guest.is_super_admin)
        self.assertTrue(verify_password_digest(double_md5('InitialAdminForTest1!'), admin.password)[0])
        self.assertFalse(verify_password_digest(double_md5('InitialAdminForTest1!'), guest.password)[0])
        self.assertTrue(verify_password_digest(double_md5('InitialGuestForTest2!'), guest.password)[0])

    def test_redeploy_does_not_replace_existing_accounts(self):
        with patch.object(User.objects, 'exists', return_value=True), \
                patch.object(User.objects, 'bulk_create') as create:
            apps.get_app_config('auto_user').new_user()
        create.assert_not_called()
