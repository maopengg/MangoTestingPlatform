# Generated by Django 4.1.5 on 2024-12-06 14:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auto_ui', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='page',
            old_name='create_Time',
            new_name='create_time',
        ),
    ]