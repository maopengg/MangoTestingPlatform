# Generated by Django 4.1.5 on 2024-05-11 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_user', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='password',
            field=models.CharField(max_length=64, null=True, verbose_name='登录密码'),
        ),
    ]