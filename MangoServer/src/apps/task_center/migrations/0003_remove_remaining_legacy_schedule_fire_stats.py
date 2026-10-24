from django.db import migrations

LEGACY_COLUMNS = (
    'success_count',
    'fail_count',
)


def drop_remaining_legacy_schedule_fire_stats(apps, schema_editor):
    table_name = 'schedule_fire'
    connection = schema_editor.connection
    if table_name not in connection.introspection.table_names():
        return

    with connection.cursor() as cursor:
        table_description = connection.introspection.get_table_description(cursor, table_name)
        existing_columns = {column.name for column in table_description}
        for column_name in LEGACY_COLUMNS:
            if column_name in existing_columns:
                schema_editor.execute(
                    f'ALTER TABLE {schema_editor.quote_name(table_name)} '
                    f'DROP COLUMN {schema_editor.quote_name(column_name)}'
                )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('task_center', '0002_remove_legacy_schedule_fire_stats'),
    ]

    operations = [
        migrations.RunPython(
            drop_remaining_legacy_schedule_fire_stats,
            migrations.RunPython.noop,
        ),
    ]
