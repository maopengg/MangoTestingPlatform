from importlib import import_module
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from django.core.management import get_commands
from django.core.management.commands.migrate import Command as DjangoMigrateCommand
from django.db import migrations

from src.apps.system.management.commands.migrate import Command


class MigrationTimeoutTests(TestCase):
    def test_mysql_migration_has_long_timeout_and_restores_runtime_options(self):
        connection = Mock(settings_dict={'ENGINE': 'src.common.database.mysql',
                                         'OPTIONS': {'read_timeout': 60, 'charset': 'utf8mb4'}})
        original = connection.settings_dict['OPTIONS']

        def execute(*args, **kwargs):
            self.assertEqual(connection.settings_dict['OPTIONS']['read_timeout'], 1800)
            self.assertEqual(connection.settings_dict['OPTIONS']['write_timeout'], 1800)
            self.assertEqual(connection.settings_dict['OPTIONS']['charset'], 'utf8mb4')
            return 'migrated'

        with patch('src.apps.system.management.commands.migrate.connections', {'default': connection}), \
                patch.object(DjangoMigrateCommand, 'execute', side_effect=execute):
            self.assertEqual(Command().execute(database='default'), 'migrated')
        self.assertIs(connection.settings_dict['OPTIONS'], original)
        self.assertEqual(connection.close.call_count, 2)
        self.assertEqual(get_commands()['migrate'], 'src.apps.system')

    def test_failure_restores_options_and_does_not_hide_error(self):
        connection = Mock(settings_dict={'ENGINE': 'django.db.backends.mysql',
                                         'OPTIONS': {'read_timeout': 3600}})
        original = connection.settings_dict['OPTIONS']
        with patch('src.apps.system.management.commands.migrate.connections', {'other': connection}), \
                patch.object(DjangoMigrateCommand, 'execute', side_effect=RuntimeError('DDL failed')):
            with self.assertRaisesRegex(RuntimeError, 'DDL failed'):
                Command().execute(database='other')
        self.assertIs(connection.settings_dict['OPTIONS'], original)

    def test_other_backends_keep_default_behavior(self):
        connection = Mock(settings_dict={'ENGINE': 'django.db.backends.sqlite3', 'OPTIONS': {}})
        with patch('src.apps.system.management.commands.migrate.connections', {'default': connection}), \
                patch.object(DjangoMigrateCommand, 'execute', return_value='unchanged'):
            self.assertEqual(Command().execute(database='default'), 'unchanged')
        connection.close.assert_not_called()


class InterruptedUserMigrationTests(TestCase):
    def test_missing_retired_column_is_skipped_but_present_column_is_removed(self):
        module = import_module('src.apps.user.migrations.0012_remove_user_last_login_time_remove_user_mailbox_and_more')
        operation = module.RemoveFieldIfExists(model_name='user', name='last_login_time')
        model = Mock()
        model._meta.get_field.return_value.column = 'last_login_time'
        state = Mock()
        state.apps.get_model.return_value = model
        editor = Mock()
        editor.connection.cursor.return_value.__enter__ = Mock(return_value=Mock())
        editor.connection.cursor.return_value.__exit__ = Mock(return_value=False)
        with patch.object(migrations.RemoveField, 'database_forwards') as remove:
            editor.connection.introspection.get_table_description.return_value = [SimpleNamespace(name='id')]
            operation.database_forwards('auto_user', editor, state, state)
            remove.assert_not_called()
            editor.connection.introspection.get_table_description.return_value = [SimpleNamespace(name='last_login_time')]
            operation.database_forwards('auto_user', editor, state, state)
            remove.assert_called_once_with('auto_user', editor, state, state)
