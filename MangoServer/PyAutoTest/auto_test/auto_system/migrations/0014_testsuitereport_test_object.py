# Generated by Django 4.1.5 on 2023-12-14 08:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_system', '0013_alter_testsuitereport_error_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='testsuitereport',
            name='test_object',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='auto_system.testobject'),
        ),
    ]