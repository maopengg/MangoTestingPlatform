# Generated by Django 4.1.5 on 2025-01-15 12:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auto_system', '0002_tasksdetails_command_alter_tasksdetails_case_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filedata',
            name='file',
        ),
        migrations.RemoveField(
            model_name='filedata',
            name='price',
        ),
        migrations.RemoveField(
            model_name='filedata',
            name='project',
        ),
        migrations.AddField(
            model_name='filedata',
            name='failed_screenshot',
            field=models.ImageField(null=True, upload_to='failed_screenshot/', verbose_name='失败截图'),
        ),
        migrations.AddField(
            model_name='filedata',
            name='test_file',
            field=models.FileField(null=True, upload_to='test_file/', verbose_name='文件'),
        ),
        migrations.AlterField(
            model_name='filedata',
            name='name',
            field=models.CharField(max_length=255, unique=True, verbose_name='文件名称'),
        ),
    ]
