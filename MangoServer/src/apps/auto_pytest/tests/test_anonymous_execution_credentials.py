from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_pytest.services.repository.git_credentials import PytestGitCredentialService


class AnonymousExecutionCredentialsTests(SimpleTestCase):
    @patch('src.apps.auto_pytest.services.repository.git_credentials.cache.set')
    @patch('src.apps.auto_pytest.services.repository.git_credentials.RepositoryGitService.provider_config')
    def test_anonymous_dispatch_does_not_require_a_cached_reference(self, config, cache_set):
        config.return_value = SimpleNamespace(access_token='')
        result = PytestGitCredentialService.issue(
            'example-executor', SimpleNamespace(id=1, credential=None), 'example-dispatch',
        )
        self.assertEqual(result, '')
        cache_set.assert_not_called()

    @patch('src.apps.auto_pytest.services.repository.git_credentials.cache.get')
    def test_anonymous_binding_does_not_read_credentials(self, cache_get):
        PytestGitCredentialService.bind(None, 'example-executor')
        cache_get.assert_not_called()
