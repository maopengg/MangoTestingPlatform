# Generated by Django 4.1.5 on 2024-02-04 09:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auto_system', '0021_cachedata'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledtasks',
            name='parallel_number',
            field=models.SmallIntegerField(null=True, verbose_name='用例执行并行数'),
        ),
        migrations.AddField(
            model_name='tasksruncaselist',
            name='sort',
            field=models.SmallIntegerField(null=True, verbose_name='api_case_id'),
        ),
        migrations.AddField(
            model_name='tasksruncaselist',
            name='test_object',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auto_system.testobject'),
        ),
    ]