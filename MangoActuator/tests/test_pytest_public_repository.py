import io
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from dulwich import porcelain
from dulwich.config import ConfigFile
from dulwich.repo import Repo

from src.services.pytest.public_repository import download_public_git_archive


class PublicRepositoryTests(TestCase):
    def test_archive_uses_requested_commit_instead_of_latest_head(self):
        with tempfile.TemporaryDirectory() as directory:
            porcelain.init(directory).close()
            file = Path(directory) / 'test_example.py'
            file.write_bytes(b'first commit\n')
            porcelain.add(directory, paths=[str(file)])
            first = porcelain.commit(directory, message=b'first', author=b'Test <test@example.com>')
            file.write_bytes(b'later commit\n')
            porcelain.add(directory, paths=[str(file)])
            porcelain.commit(directory, message=b'later', author=b'Test <test@example.com>')
            with patch('src.services.pytest.public_repository.porcelain.clone', return_value=Repo(directory)) as clone:
                data = download_public_git_archive('https://example.com/example/repository.git', first.decode())
            self.assertIsInstance(clone.call_args.kwargs['config'], ConfigFile)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                self.assertEqual(archive.read('repository/test_example.py'), b'first commit\n')

    def test_rejects_local_and_credential_urls(self):
        for url in ['file:///tmp/repo', 'https://user:secret@example.com/repo.git']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                download_public_git_archive(url, 'a' * 40)
