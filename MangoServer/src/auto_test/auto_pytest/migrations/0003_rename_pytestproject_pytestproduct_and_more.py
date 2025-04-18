# Generated by Django 4.1.5 on 2025-03-09 22:49

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_system', '0007_alter_testsuite_tasks'),
        ('auto_pytest', '0002_remove_pytesttestfile_module'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='PytestProject',
            new_name='PytestProduct',
        ),
        migrations.AlterField(
            model_name='pytestact',
            name='module',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='auto_system.productmodule'),
        ),
        migrations.AlterField(
            model_name='pytestcase',
            name='module',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='auto_system.productmodule'),
        ),
        migrations.AlterField(
            model_name='pytesttools',
            name='module',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='auto_system.productmodule'),
        ),
        migrations.AlterModelTable(
            name='pytestproduct',
            table='pytest_product',
        ),
        migrations.DeleteModel(
            name='PytestProjectModule',
        ),
    ]
