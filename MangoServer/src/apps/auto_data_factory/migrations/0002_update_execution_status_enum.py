from django.db import migrations, models
from django.db.models import Case, IntegerField, Value, When


def forwards(apps, schema_editor):
    DataFactoryExecution = apps.get_model('auto_data_factory', 'DataFactoryExecution')
    DataFactoryExecution.objects.filter(status__in=[1, 2, 3, 4]).update(
        status=Case(
            When(status=1, then=Value(2)),  # 待执行 -> 待开始
            When(status=2, then=Value(1)),  # 成功 -> 通过
            When(status=3, then=Value(0)),  # 失败 -> 失败
            When(status=4, then=Value(3)),  # 进行中 -> 进行中
            output_field=IntegerField(),
        )
    )


def backwards(apps, schema_editor):
    DataFactoryExecution = apps.get_model('auto_data_factory', 'DataFactoryExecution')
    DataFactoryExecution.objects.filter(status__in=[0, 1, 2, 3]).update(
        status=Case(
            When(status=0, then=Value(3)),  # 失败 -> 失败
            When(status=1, then=Value(2)),  # 通过 -> 成功
            When(status=2, then=Value(1)),  # 待开始 -> 待执行
            When(status=3, then=Value(4)),  # 进行中 -> 进行中
            output_field=IntegerField(),
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ('auto_data_factory', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datafactoryexecution',
            name='status',
            field=models.SmallIntegerField(
                choices=[
                    (0, '失败'),
                    (1, '通过'),
                    (2, '待开始'),
                    (3, '进行中'),
                ],
                db_index=True,
                default=2,
                verbose_name='执行状态',
            ),
        ),
        migrations.RunPython(forwards, backwards),
    ]
