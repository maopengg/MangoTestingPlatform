# Generated by Django 4.1.5 on 2024-06-19 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_user', '0002_remove_user_last_login_time_alter_user_mailbox'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_login_time',
            field=models.DateTimeField(null=True, verbose_name='修改时间'),
        ),
        migrations.AlterField(
            model_name='user',
            name='nickname',
            field=models.CharField(max_length=64, null=True, unique=True, verbose_name='昵称'),
        ),
    ]
