import io
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from dulwich import porcelain
from dulwich.config import ConfigFile
from dulwich.repo import Repo

from src.apps.auto_pytest.exceptions import AutoPytestError
from src.apps.auto_pytest.services.repository_credentials import PytestRepositoryCredentialService as Credentials
from src.apps.auto_pytest.services.git_management.public_repository import download_public_git_archive
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService


class PublicRepositoryAccessTests(SimpleTestCase):
    def credential(self, auth_type='token'):
        return SimpleNamespace(auth_type=auth_type, username='example-user', save=Mock())

    def test_anonymous_none_empty_and_null_never_save_a_secret(self):
        for value in ('none', '', None):
            existing = self.credential()
            self.assertIsNone(Credentials.save_from_request({'credential_auth_type': value}, existing))
            existing.save.assert_not_called()
        self.assertIsNone(Credentials.save_from_request({}, None))

    def test_blank_secret_preserves_existing_encrypted_secret_and_username(self):
        existing = self.credential('username_password')
        existing.secret_ciphertext = b'existing-ciphertext'
        with patch.object(Credentials, 'set_secret') as encrypt:
            self.assertIs(Credentials.save_from_request({'credential_secret': ''}, existing), existing)
        self.assertEqual(existing.username, 'example-user')
        self.assertEqual(existing.secret_ciphertext, b'existing-ciphertext')
        encrypt.assert_not_called()

    def test_changing_auth_type_requires_a_new_secret(self):
        with self.assertRaises(AutoPytestError):
            Credentials.save_from_request({'credential_auth_type': 'username_password'}, self.credential())
        with self.assertRaises(AutoPytestError):
            Credentials.save_from_request({'credential_auth_type': 'token'}, None)
        with self.assertRaises(AutoPytestError):
            Credentials.save_from_request({'credential_auth_type': 'invalid'}, None)

    def test_password_auth_requires_username(self):
        with self.assertRaises(AutoPytestError):
            Credentials.save_from_request({'credential_auth_type': 'username_password', 'credential_secret': 'example'}, None)

    def test_token_and_password_are_stored_in_the_correct_fields(self):
        for auth_type in ('token', 'username_password'):
            existing = self.credential(auth_type)
            with patch.object(Credentials, 'set_secret') as encrypt:
                Credentials.save_from_request({
                    'credential_auth_type': auth_type, 'credential_username': 'test-user', 'credential_secret': 'example-secret',
                }, existing, operator_id=7)
            encrypt.assert_called_once_with(existing,
                secret='example-secret' if auth_type == 'token' else '',
                password='example-secret' if auth_type == 'username_password' else '')
            self.assertEqual(existing.update_user_id, 7)
            existing.save.assert_called_once()

    def test_public_gitee_connection_does_not_require_a_token(self):
        repository = SimpleNamespace(id=1, provider='gitee', default_branch='master', remote_project='example/repository')
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = SimpleNamespace(commit_hash='a' * 40)
        client.list_branches.return_value = [SimpleNamespace(name='master')]
        with patch.object(service, 'api_client', return_value=client):
            self.assertTrue(service.test_connection()['success'])

    def test_public_archive_uses_git_and_preserves_file_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            porcelain.init(directory).close()
            content = Path(directory) / 'test_example.py'
            content.write_bytes(b'def test_example():\n    assert True\n')
            porcelain.add(directory, paths=[str(content)])
            commit = porcelain.commit(directory, message=b'example', author=b'Example <test@example.com>')
            with patch('src.apps.auto_pytest.services.git_management.public_repository.porcelain.clone',
                       return_value=Repo(directory)) as clone:
                data = download_public_git_archive('https://gitee.com/example/repository.git', commit.decode())
            self.assertIsInstance(clone.call_args.kwargs['config'], ConfigFile)
            self.assertTrue(clone.call_args.kwargs['bare'])
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.assertEqual(archive.read('repository/test_example.py'), content.read_bytes())

    def test_public_archive_rejects_credential_urls_and_local_paths(self):
        for url in ('file:///tmp/repository', 'https://user:password@example.com/repo.git'):
            with self.assertRaises(AutoPytestError):
                download_public_git_archive(url, 'a' * 40)

    def test_saving_anonymous_detaches_old_credential_after_connection_succeeds(self):
        from src.apps.auto_pytest.api.views import pytest_repository as view_module
        from src.apps.auto_pytest.models import PytestRepository, PytestRepositoryCredential
        old = PytestRepositoryCredential(id=5, auth_type='token', secret_ciphertext=b'old')
        repository = PytestRepository(id=1, name='Example', provider='gitee',
            repo_url='https://gitee.com/example/repository.git', api_base_url='https://gitee.com',
            remote_project='example/repository', default_branch='master', active_branch='master', credential=old)
        events = []
        with patch.object(view_module, '_repository', return_value=repository), \
                patch.object(view_module, '_request_user_id', return_value=None), \
                patch.object(view_module.PytestRepository.objects, 'exclude') as exclude, \
                patch.object(repository, 'save'), \
                patch.object(old, 'delete', side_effect=lambda: events.append('delete')), \
                patch.object(view_module, 'PytestRepositorySerializer') as serializer, \
                patch.object(RepositoryGitService, 'test_connection', side_effect=lambda: events.append('test')):
            exclude.return_value.filter.return_value.exists.return_value = False
            serializer.return_value.data = {}
            request = SimpleNamespace(data={'id': 1, 'credential_auth_type': 'none'})
            response = view_module.PytestRepositoryViews._save_repository.__wrapped__(
                view_module.PytestRepositoryViews(), request)
        self.assertEqual(response.data['code'], 200)
        self.assertIsNone(repository.credential)
        self.assertEqual(events, ['test', 'delete'])
