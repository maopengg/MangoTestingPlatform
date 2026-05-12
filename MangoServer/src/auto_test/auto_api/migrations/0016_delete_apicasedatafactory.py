from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auto_data_factory', '0004_datafactorycaseconfig'),
        ('auto_api', '0015_alter_apicasedatafactory_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ApiCaseDataFactory',
        ),
    ]
