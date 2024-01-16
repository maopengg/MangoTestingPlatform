# Generated by Django 4.1.5 on 2023-12-11 06:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_api', '0002_apicasedetailed_apiinfo_remove_apicasegroup_project_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apicasedetailed',
            name='ass',
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='ass_response_value',
            field=models.JSONField(null=True, verbose_name='响应值断言'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='ass_response_whole',
            field=models.JSONField(null=True, verbose_name='响应全匹配断言'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='ass_sql',
            field=models.JSONField(null=True, verbose_name='sql断言'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='dump_data',
            field=models.JSONField(null=True, verbose_name='数据清除'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='file',
            field=models.CharField(max_length=2048, null=True, verbose_name='文件'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='front_sql',
            field=models.JSONField(null=True, verbose_name='前置sql'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='posterior_response',
            field=models.JSONField(null=True, verbose_name='后置响应处理'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='posterior_sql',
            field=models.JSONField(null=True, verbose_name='后置sql'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='response_code',
            field=models.CharField(max_length=64, null=True, verbose_name='响应code码'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='response_headers',
            field=models.TextField(null=True, verbose_name='响应headers'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='response_text',
            field=models.TextField(null=True, verbose_name='响应文本'),
        ),
        migrations.AddField(
            model_name='apicasedetailed',
            name='response_time',
            field=models.CharField(max_length=64, null=True, verbose_name='响应时间'),
        ),
    ]