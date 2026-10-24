from django.db import migrations, models

SCENE_CHOICES = [
    ('unclassified', '未分类'),
    ('routine_regression', '日常回归'),
    ('release_verification', '发布验证'),
    ('inspection', '巡检'),
    ('stability_monitoring', '稳定性监测'),
    ('data_verification', '数据校验'),
]

SCOPE_CHOICES = [
    ('unclassified', '未分类'),
    ('full_product', '产品全量'),
    ('module', '模块回归'),
    ('core_link', '核心链路'),
    ('selected_cases', '指定用例'),
]


def classify_existing_tasks(apps, schema_editor):
    Tasks = apps.get_model('auto_system', 'Tasks')
    TestSuite = apps.get_model('auto_system', 'TestSuite')

    for task in Tasks.objects.all().iterator(chunk_size=200):
        name = str(task.name or '')
        if '巡检' in name:
            scene = 'inspection'
        elif any(keyword in name for keyword in ('发布', '发版')):
            scene = 'release_verification'
        elif '稳定' in name:
            scene = 'stability_monitoring'
        elif any(keyword in name for keyword in ('数据校验', '数据核对', '一致性')):
            scene = 'data_verification'
        else:
            scene = 'routine_regression'

        if task.module_id:
            scope = 'module'
        elif '全量' in name:
            scope = 'full_product'
        elif any(keyword in name for keyword in ('核心', '主链路', '主流程', '冒烟')):
            scope = 'core_link'
        else:
            scope = 'selected_cases'

        Tasks.objects.filter(id=task.id).update(
            execution_scene=scene,
            execution_scope=scope,
        )

    for task in Tasks.objects.only('id', 'execution_scene', 'execution_scope').iterator(chunk_size=200):
        TestSuite.objects.filter(tasks_id=task.id).update(
            execution_scene=task.execution_scene,
            execution_scope=task.execution_scope,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('auto_system', '0038_executortask_delete_socketmessage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tasks',
            name='execution_scene',
            field=models.CharField(
                choices=SCENE_CHOICES,
                db_index=True,
                default='unclassified',
                max_length=32,
                verbose_name='执行场景',
            ),
        ),
        migrations.AddField(
            model_name='tasks',
            name='execution_scope',
            field=models.CharField(
                choices=SCOPE_CHOICES,
                db_index=True,
                default='unclassified',
                max_length=32,
                verbose_name='执行范围',
            ),
        ),
        migrations.AddField(
            model_name='testsuite',
            name='execution_scene',
            field=models.CharField(
                choices=SCENE_CHOICES,
                db_index=True,
                default='unclassified',
                max_length=32,
                verbose_name='执行场景快照',
            ),
        ),
        migrations.AddField(
            model_name='testsuite',
            name='execution_scope',
            field=models.CharField(
                choices=SCOPE_CHOICES,
                db_index=True,
                default='unclassified',
                max_length=32,
                verbose_name='执行范围快照',
            ),
        ),
        migrations.RunPython(classify_existing_tasks, migrations.RunPython.noop),
    ]
