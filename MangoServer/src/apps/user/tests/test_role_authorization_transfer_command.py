import json
import stat
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from src.apps.user.services.authorization.role_authorization_transfer import RoleAuthorizationTransferService


class RoleAuthorizationTransferCommandTests(SimpleTestCase):
    def test_export_is_private_and_does_not_overwrite_backup(self):
        backup = {'format': 'mango-role-authorization-v1', 'roles': []}
        with TemporaryDirectory() as directory, patch.object(
                RoleAuthorizationTransferService, 'export_legacy', return_value=backup):
            path = Path(directory) / 'roles.json'
            call_command('transfer_role_authorizations', export_path=str(path), stdout=StringIO())
            self.assertEqual(json.loads(path.read_text()), backup)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            with self.assertRaises(CommandError):
                call_command('transfer_role_authorizations', export_path=str(path), stdout=StringIO())
            self.assertEqual(json.loads(path.read_text()), backup)

    def test_import_is_dry_run_unless_apply_is_explicit(self):
        backup = {'format': 'mango-role-authorization-v1', 'roles': []}
        with TemporaryDirectory() as directory, patch.object(
                RoleAuthorizationTransferService, 'import_backup',
                return_value={'roles': 0, 'changed': 0, 'pending': 0}) as transfer:
            path = Path(directory) / 'roles.json'
            path.write_text(json.dumps(backup))
            call_command('transfer_role_authorizations', import_path=str(path), stdout=StringIO())
            transfer.assert_called_with(backup, apply=False)
            call_command('transfer_role_authorizations', import_path=str(path), apply=True, stdout=StringIO())
            transfer.assert_called_with(backup, apply=True)

    def test_apply_cannot_be_used_for_export(self):
        with patch.object(RoleAuthorizationTransferService, 'export_legacy') as export:
            with self.assertRaises(CommandError):
                call_command('transfer_role_authorizations', export_path='unused.json', apply=True)
            export.assert_not_called()
