# Generated by Django 4.1.5 on 2024-10-08 16:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_system', '0005_remove_database_project_product_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='database',
            name='status',
            field=models.SmallIntegerField(null=True, verbose_name='是否启用'),
        ),
    ]
