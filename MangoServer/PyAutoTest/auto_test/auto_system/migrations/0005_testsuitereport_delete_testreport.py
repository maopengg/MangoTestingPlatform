# Generated by Django 4.1.5 on 2023-10-25 09:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_user', '0001_initial'),
        ('auto_system', '0004_rename_task_name_scheduledtasks_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestSuiteReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
                ('type', models.SmallIntegerField(null=True, verbose_name='类型')),
                ('name', models.CharField(max_length=64, verbose_name='用例名称')),
                ('run_state', models.SmallIntegerField(null=True, verbose_name='执行状态')),
                ('state', models.SmallIntegerField(null=True, verbose_name='测试结果')),
                ('project',
                 models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auto_user.project')),
            ],
            options={
                'db_table': 'test_suite_report',
                'ordering': ['-id'],
            },
        ),
        migrations.DeleteModel(
            name='TestReport',
        ),
    ]