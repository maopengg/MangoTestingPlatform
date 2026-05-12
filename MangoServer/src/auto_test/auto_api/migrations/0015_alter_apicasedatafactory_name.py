from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_api', '0014_remove_apicasedatafactory_alias_and_output_mapping'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apicasedatafactory',
            name='name',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='数据名称'),
        ),
    ]
