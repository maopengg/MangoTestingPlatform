# Generated by Django 4.1.5 on 2025-02-18 15:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auto_ui', '0004_uicase_parametrize_alter_page_module_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagestepsdetailed',
            name='ele_name',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auto_ui.pageelement'),
        ),
    ]
