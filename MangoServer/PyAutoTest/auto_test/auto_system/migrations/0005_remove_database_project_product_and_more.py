# Generated by Django 4.1.5 on 2024-10-08 14:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auto_user', '0006_user_config'),
        ('auto_system', '0004_remove_scheduledtasks_test_obj_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='database',
            name='project_product',
        ),
        migrations.RemoveField(
            model_name='noticeconfig',
            name='project',
        ),
        migrations.AlterField(
            model_name='database',
            name='environment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auto_user.testobject'),
        ),
        migrations.AlterField(
            model_name='noticeconfig',
            name='environment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='auto_user.testobject'),
        ),
    ]
