# Generated by Django 4.1.5 on 2023-10-30 03:11

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_ui', '0013_uipagestepsresult_case_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='uieleresult',
            name='case_id',
            field=models.IntegerField(null=True, verbose_name='用例ID'),
        ),
    ]