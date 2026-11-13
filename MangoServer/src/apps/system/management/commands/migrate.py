"""Allow slow MySQL DDL without changing normal API query timeouts."""
from django.core.management.commands.migrate import Command as DjangoMigrateCommand
from django.db import connections


class Command(DjangoMigrateCommand):
    def execute(self, *args, **options):
        connection = connections[options.get('database', 'default')]
        if not connection.settings_dict['ENGINE'].endswith('.mysql'):
            return super().execute(*args, **options)
        original = connection.settings_dict.get('OPTIONS', {})
        migration_options = dict(original)
        for key in ('read_timeout', 'write_timeout'):
            migration_options[key] = max(1800, original.get(key, 0) or 0)
        connection.close()
        connection.settings_dict['OPTIONS'] = migration_options
        try:
            return super().execute(*args, **options)
        finally:
            connection.close()
            connection.settings_dict['OPTIONS'] = original
