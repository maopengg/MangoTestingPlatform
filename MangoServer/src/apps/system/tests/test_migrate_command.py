from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from src.apps.system.management.commands.migrate import (
    ALREADY_APPLIED_RELOCATION_MIGRATIONS,
    RELOCATED_TABLES,
    TEST_CENTER_BASELINES,
    Command,
)


class TestCenterMigrationBootstrapTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()
        self.connection = MagicMock()
        self.connection.introspection.table_names.return_value = list(RELOCATED_TABLES)

    @patch("src.apps.system.management.commands.migrate.MigrationRecorder")
    @patch("src.apps.system.management.commands.migrate.connections")
    def test_records_baseline_for_an_existing_relocated_database(self, connections, recorder_cls):
        connections.__getitem__.return_value = self.connection
        recorder = recorder_cls.return_value
        recorder.applied_migrations.return_value = {
            next(iter(ALREADY_APPLIED_RELOCATION_MIGRATIONS)),
        }

        self.command._record_existing_test_center_baseline("default")

        self.assertEqual(
            list(TEST_CENTER_BASELINES),
            [call.args for call in recorder.record_applied.call_args_list],
        )

    @patch("src.apps.system.management.commands.migrate.MigrationRecorder")
    @patch("src.apps.system.management.commands.migrate.connections")
    def test_does_not_fake_baseline_for_a_new_database(self, connections, recorder_cls):
        connections.__getitem__.return_value = self.connection
        recorder = recorder_cls.return_value
        recorder.applied_migrations.return_value = set()

        self.command._record_existing_test_center_baseline("default")

        recorder.record_applied.assert_not_called()
    @patch("src.apps.system.management.commands.migrate.MigrationRecorder")
    @patch("src.apps.system.management.commands.migrate.connections")
    def test_rejects_incomplete_historical_schema(self, connections, recorder_cls):
        connections.__getitem__.return_value = self.connection
        recorder = recorder_cls.return_value
        recorder.applied_migrations.return_value = {
            next(iter(ALREADY_APPLIED_RELOCATION_MIGRATIONS)),
        }
        self.connection.introspection.table_names.return_value = []

        with self.assertRaises(CommandError):
            self.command._record_existing_test_center_baseline("default")

        recorder.record_applied.assert_not_called()


class ProjectProductOwnerMigrationTests(SimpleTestCase):
    def test_new_database_creates_owner_relation_without_removed_executor_field(self):
        migration = import_module('src.apps.system.migrations.0050_ensure_project_product_owners')
        through_model = MagicMock()
        product = MagicMock()
        product._meta.get_field.return_value.remote_field.through = through_model
        test_object = MagicMock()
        test_object._meta.concrete_fields = [SimpleNamespace(name='id'), SimpleNamespace(name='name')]
        apps = MagicMock()
        apps.get_model.side_effect = [product, test_object]
        schema_editor = MagicMock()
        schema_editor.connection.introspection.table_names.return_value = [
            migration.PROJECT_PRODUCT_TABLE, migration.TEST_OBJECT_TABLE, migration.USER_TABLE,
        ]

        migration.ensure_project_product_owners(apps, schema_editor)

        schema_editor.create_model.assert_called_once_with(through_model)
        test_object.objects.using.assert_not_called()
