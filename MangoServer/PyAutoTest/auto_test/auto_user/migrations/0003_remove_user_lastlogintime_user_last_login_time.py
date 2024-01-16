# Generated by Django 4.1.5 on 2023-11-20 09:27

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_user', '0002_rename_module_name_projectmodule_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='lastLoginTime',
        ),
        migrations.AddField(
            model_name='user',
            name='last_login_time',
            field=models.DateTimeField(null=True, verbose_name='上次登录时间'),
        ),
    ]