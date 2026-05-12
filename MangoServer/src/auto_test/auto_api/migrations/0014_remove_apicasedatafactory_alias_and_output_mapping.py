from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auto_api', '0013_apicasedatafactory'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apicasedatafactory',
            name='alias',
        ),
        migrations.RemoveField(
            model_name='apicasedatafactory',
            name='output_mapping',
        ),
    ]
