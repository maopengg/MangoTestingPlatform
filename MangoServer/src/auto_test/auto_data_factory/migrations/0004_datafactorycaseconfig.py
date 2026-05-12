from django.db import migrations, models
import django.db.models.deletion


def copy_api_case_data_factory(apps, schema_editor):
    try:
        ApiCaseDataFactory = apps.get_model('auto_api', 'ApiCaseDataFactory')
    except LookupError:
        return
    DataFactoryCaseConfig = apps.get_model('auto_data_factory', 'DataFactoryCaseConfig')
    rows = []
    for item in ApiCaseDataFactory.objects.all():
        rows.append(DataFactoryCaseConfig(
            id=item.id,
            create_time=item.create_time,
            update_time=item.update_time,
            source_type=1,
            source_id=item.case_id,
            template_id=item.template_id,
            name=item.name,
            stage=item.stage,
            sort=item.sort,
            field_overrides=item.field_overrides or {},
            cleanup_strategy=item.cleanup_strategy,
            status=item.status,
        ))
    if rows:
        DataFactoryCaseConfig.objects.bulk_create(rows)


class Migration(migrations.Migration):

    dependencies = [
        ('auto_api', '0015_alter_apicasedatafactory_name'),
        ('auto_data_factory', '0003_add_module_scope'),
        ('auto_data_factory', '0003_alter_datafactoryexecution_source_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataFactoryCaseConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
                ('source_type', models.SmallIntegerField(choices=[(1, 'API用例'), (2, 'UI用例')], db_index=True, verbose_name='用例类型')),
                ('source_id', models.IntegerField(db_index=True, verbose_name='用例ID')),
                ('name', models.CharField(blank=True, max_length=64, null=True, verbose_name='数据名称')),
                ('stage', models.SmallIntegerField(default=1, verbose_name='执行阶段')),
                ('sort', models.IntegerField(default=0, verbose_name='执行顺序')),
                ('field_overrides', models.JSONField(default=dict, verbose_name='字段覆盖')),
                ('cleanup_strategy', models.SmallIntegerField(blank=True, null=True, verbose_name='清理策略覆盖')),
                ('status', models.SmallIntegerField(db_index=True, default=1, verbose_name='状态')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='auto_data_factory.datafactorytemplate')),
            ],
            options={
                'db_table': 'data_factory_case_config',
                'ordering': ['sort', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='datafactorycaseconfig',
            index=models.Index(fields=['source_type', 'source_id', 'stage', 'status'], name='data_factor_source__0d0fdb_idx'),
        ),
        migrations.RunPython(copy_api_case_data_factory, migrations.RunPython.noop),
    ]
