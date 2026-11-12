import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from src.apps.auto_pytest.api.views.pytest_repository import PytestRepositoryViews
from src.apps.auto_pytest.enums import PytestRepositorySyncStatusEnum
from src.apps.auto_pytest.exceptions import (
    AutoPytestError, PYTEST_REPOSITORY_CONFIG_INVALID, PYTEST_REPOSITORY_BRANCH_CODE_INVALID,
)
from src.apps.auto_pytest.models import PytestCase, PytestProduct, PytestRepository
from src.apps.auto_pytest.services.repository.repository_service import RepositoryGitService
from src.apps.user.models import User


class RepositoryEditingTests(TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        settings = override_settings(GIT_WORKSPACE_DIR=workspace.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = User.objects.create(username='repository_editor', name='仓库编辑', password='unused')
        self.repository = PytestRepository.objects.create(
            name='Example Repository', provider='gitlab',
            repo_url='https://git.example.com/team/original.git',
            api_base_url='https://git.example.com', remote_project='team/original',
            default_branch='main', active_branch='feature/example', current_commit='old-commit',
            sync_status=PytestRepositorySyncStatusEnum.FAILED.value,
            last_sync_time=timezone.now(), last_sync_error='old-error',
        )

    def save_repository(self, **changes):
        data = {
            'id': self.repository.id, 'name': self.repository.name,
            'provider': self.repository.provider, 'repo_url': self.repository.repo_url,
            'api_base_url': self.repository.api_base_url, 'remote_project': self.repository.remote_project,
            'default_branch': self.repository.default_branch,
            **changes,
        }
        request = SimpleNamespace(data=data, user=SimpleNamespace(id=self.user.id))
        return PytestRepositoryViews().save_repository(request)

    @patch.object(RepositoryGitService, 'test_connection', return_value={'success': True})
    def test_edit_source_preserves_repository_project_and_case_ids(self, connection):
        product = PytestProduct.objects.create(
            repository=self.repository, name='Example Project', file_name='tests', init_file='__init__.py',
        )
        case = PytestCase.objects.create(
            project_product=product, name='Example Case', file_name='test_example.py',
            file_path='tests/test_example.py', file_update_time=timezone.now(),
        )
        response = self.save_repository(
            provider='github', repo_url='https://github.com/example/repository.git',
            api_base_url='', remote_project='example/repository', default_branch='master',
        )

        self.assertEqual(response.data['code'], 200)
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.provider, 'github')
        self.assertEqual(self.repository.api_base_url, 'https://api.github.com')
        self.assertEqual(self.repository.active_branch, 'master')
        self.assertIsNone(self.repository.current_commit)
        self.assertEqual(self.repository.sync_status, PytestRepositorySyncStatusEnum.IDLE.value)
        self.assertIsNone(self.repository.last_sync_error)
        self.assertIsNone(self.repository.last_sync_time)
        self.assertEqual(PytestProduct.objects.get(id=product.id).repository_id, self.repository.id)
        self.assertEqual(PytestCase.objects.get(id=case.id).project_product_id, product.id)
        connection.assert_called_once()

    @patch.object(RepositoryGitService, 'test_connection', return_value={'success': True})
    def test_changed_url_derives_remote_project_when_left_empty(self, connection):
        response = self.save_repository(
            repo_url='https://git.example.com/team/new.git', remote_project='',
        )
        self.assertEqual(response.data['code'], 200)
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.remote_project, 'team/new')
        connection.assert_called_once()

    @patch.object(RepositoryGitService, 'test_connection', side_effect=AutoPytestError(PYTEST_REPOSITORY_CONFIG_INVALID))
    def test_invalid_new_source_rolls_back_existing_configuration(self, connection):
        response = self.save_repository(remote_project='team/missing')
        self.assertNotEqual(response.data['code'], 200)
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.remote_project, 'team/original')
        self.assertEqual(self.repository.current_commit, 'old-commit')
        connection.assert_called_once()

    @patch.object(RepositoryGitService, 'test_connection')
    def test_name_only_change_preserves_active_branch_and_sync_state(self, connection):
        response = self.save_repository(name='Renamed Repository')
        self.assertEqual(response.data['code'], 200)
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.name, 'Renamed Repository')
        self.assertEqual(self.repository.active_branch, 'feature/example')
        self.assertEqual(self.repository.current_commit, 'old-commit')
        connection.assert_not_called()

    @patch.object(RepositoryGitService, 'validate_source_change',
                  side_effect=AutoPytestError(PYTEST_REPOSITORY_BRANCH_CODE_INVALID))
    @patch.object(RepositoryGitService, 'test_connection')
    def test_unpushed_edits_prevent_switching_source_until_resolved(self, connection, validate):
        response = self.save_repository(remote_project='team/new')
        self.assertNotEqual(response.data['code'], 200)
        self.repository.refresh_from_db()
        self.assertEqual(self.repository.remote_project, 'team/original')
        self.assertEqual(self.repository.current_commit, 'old-commit')
        validate.assert_called_once()
        connection.assert_not_called()
