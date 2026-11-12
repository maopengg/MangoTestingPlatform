from src.apps.user.services.authorization.http_permission_registry import permission_for_view
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from src.apps.system.api.views.email_test import EmailTestViews
from src.apps.system.services.configuration.email_test import EmailConfigTestService
from src.apps.user.exceptions import USER_CREDENTIAL_EMAIL_CONFIG_FAILED, UserError


class EmailConfigTestTests(SimpleTestCase):
    def request(self, recipient):
        view = EmailTestViews.as_view({'post': 'test'}, authentication_classes=[], permission_classes=[])
        return view(APIRequestFactory().post('/system/email/test', {'recipient': recipient}, format='json'))

    @patch('src.apps.system.services.configuration.email_test.UserCredentialService.send_email')
    def test_service_uses_shared_mail_transport(self, send):
        EmailConfigTestService.send('tester@example.com')
        self.assertEqual(send.call_args.kwargs['email'], 'tester@example.com')
        self.assertEqual(send.call_args.kwargs['subtype'], 'plain')

    @patch('src.apps.system.api.views.email_test.EmailConfigTestService.send')
    def test_invalid_recipient_never_sends(self, send):
        response = self.request('invalid')
        send.assert_not_called()
        self.assertNotEqual(response.data['code'], 200)

    @patch('src.apps.system.api.views.email_test.EmailConfigTestService.send')
    def test_success_reports_submission(self, send):
        response = self.request('tester@example.com')
        send.assert_called_once_with('tester@example.com')
        self.assertTrue(response.data['data']['status'])

    @patch('src.apps.system.api.views.email_test.EmailConfigTestService.send')
    def test_failure_does_not_expose_transport_details(self, send):
        send.side_effect = UserError(USER_CREDENTIAL_EMAIL_CONFIG_FAILED, error='secret-transport-details')
        response = self.request('tester@example.com')
        self.assertFalse(response.data['data']['status'])
        self.assertNotIn('secret-transport-details', str(response.data))

    def test_requires_settings_debug_permission(self):
        self.assertEqual(permission_for_view(EmailTestViews, 'test'), 'system.settings:change')
