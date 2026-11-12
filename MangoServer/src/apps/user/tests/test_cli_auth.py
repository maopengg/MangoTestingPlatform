import base64
import hashlib
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from src.apps.user.services.authentication.cli_auth import CliAuthService

TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'cli-auth-tests',
    }
}


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')


@override_settings(CACHES=TEST_CACHES)
class CliAuthServiceTests(SimpleTestCase):
    def setUp(self):
        self.verifier = 'v' * 64
        self.redirect_uri = 'http://127.0.0.1:39123/callback'
        self.user = SimpleNamespace(id=7, username='tester@example.com')

    def create_code(self):
        return CliAuthService.create_code(
            token='page.jwt.token',
            user=self.user,
            redirect_uri=self.redirect_uri,
            state='s' * 43,
            code_challenge=pkce_challenge(self.verifier),
        )

    def test_pkce_code_is_exchanged_once(self):
        created = self.create_code()
        result = CliAuthService.exchange_code(
            code=created['code'],
            code_verifier=self.verifier,
            redirect_uri=self.redirect_uri,
        )
        self.assertEqual(result['token'], 'page.jwt.token')
        self.assertEqual(result['user_id'], 7)
        self.assertIsNone(CliAuthService.exchange_code(
            code=created['code'],
            code_verifier=self.verifier,
            redirect_uri=self.redirect_uri,
        ))

    def test_wrong_verifier_consumes_code(self):
        created = self.create_code()
        self.assertIsNone(CliAuthService.exchange_code(
            code=created['code'],
            code_verifier='x' * 64,
            redirect_uri=self.redirect_uri,
        ))
        self.assertIsNone(CliAuthService.exchange_code(
            code=created['code'],
            code_verifier=self.verifier,
            redirect_uri=self.redirect_uri,
        ))

    def test_redirect_only_accepts_ipv4_loopback_callback(self):
        self.assertTrue(CliAuthService.validate_redirect_uri(self.redirect_uri))
        for invalid in (
                'https://127.0.0.1:39123/callback',
                'http://localhost:39123/callback',
                'http://127.0.0.1:39123/other',
                'http://127.0.0.1:39123/callback?next=1',
                'http://example.com:39123/callback',
        ):
            self.assertFalse(CliAuthService.validate_redirect_uri(invalid))

    def test_cli_version_endpoint_accepts_only_current_platform_version(self):
        matched = self.client.get('/api/cli/auth/version', {'version': '7.2.5'})
        self.assertEqual(matched.status_code, 200)
        self.assertEqual(matched.json()['code'], 200)
        outdated = self.client.get('/api/cli/auth/version', {'version': '7.1.0'})
        self.assertEqual(outdated.status_code, 200)
        self.assertEqual(outdated.json()['code'], 300)
        self.assertEqual(outdated.json()['data']['latest_version'], '7.2.5')
