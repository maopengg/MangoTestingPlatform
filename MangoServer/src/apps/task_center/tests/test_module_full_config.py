from django.test import TestCase

from src.apps.task_center.api.serializers.tasks import TasksSerializers
from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.models import Tasks, TimeTasks
from src.apps.task_center.services.selection.module_full_config import ModuleFullTaskConfigService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import NoticeGroup, ProductModule, Project, ProjectProduct
from src.apps.user.models import User


class ModuleFullTaskConfigServiceTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='模块全量配置测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.parent = ProductModule.objects.create(
            project_product=self.product,
            name='订单中心',
            level=1,
        )
        self.module = ProductModule.objects.create(
            project_product=self.product,
            parent=self.parent,
            name='订单查询',
            level=2,
        )
        self.owner = User.objects.create(
            name='模块全量负责人',
            username='module_full_task_owner',
            password='pwd',
        )
        self.strategy = TimeTasks.objects.create(name='每日回归', cron='0 2 * * *')

    def row(self, **overrides):
        data = {
            'name': '订单查询模块全量任务',
            'module_id': self.module.id,
            'test_envs': [EnvironmentEnum.TEST.value],
            'case_types': [0],
            'execution_scenes': [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value],
            'timing_strategies': [self.strategy.id],
            'case_people': self.owner.id,
            'api_concurrency_limit': 1,
            'is_notice': 0,
            'notice_group': None,
            'fail_notice': 0,
            'status': 1,
        }
        data.update(overrides)
        return data

    def test_required_name_is_validated(self):
        with self.assertRaises(TaskCenterError):
            ModuleFullTaskConfigService.replace(
                self.product.id,
                [self.row(name='')],
                update_user_id=self.owner.id,
            )

    def test_same_module_can_save_multiple_unique_rows(self):
        result = ModuleFullTaskConfigService.replace(
            self.product.id,
            [self.row(), self.row(case_types=[1])],
            update_user_id=self.owner.id,
        )

        self.assertEqual(result['create_count'], 2)
        self.assertEqual(Tasks.objects.count(), 2)
        self.assertEqual(
            {task.case_types[0] for task in Tasks.objects.all()},
            {0, 1},
        )

    def test_same_row_can_save_multiple_filters(self):
        ModuleFullTaskConfigService.replace(
            self.product.id,
            [self.row(
                test_envs=[EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value],
                case_types=[0, 1],
                execution_scenes=[
                    AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
                    AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
                ],
            )],
            update_user_id=self.owner.id,
        )

        task = Tasks.objects.get()
        self.assertEqual(task.test_envs, [EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value])
        self.assertEqual(task.case_types, [0, 1])
        self.assertEqual(task.execution_scenes, [
            AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
            AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
        ])

    def test_notice_group_is_preserved_when_notice_is_disabled(self):
        notice_group = NoticeGroup.objects.create(
            project=self.product.project,
            name='模块全量通知组',
        )

        ModuleFullTaskConfigService.replace(
            self.product.id,
            [self.row(is_notice=0, notice_group=notice_group.id)],
            update_user_id=self.owner.id,
        )

        task = Tasks.objects.get()
        self.assertEqual(task.is_notice, 0)
        self.assertEqual(task.notice_group_id, notice_group.id)

    def test_removed_row_is_deleted(self):
        ModuleFullTaskConfigService.replace(self.product.id, [self.row()])
        task = Tasks.objects.get()

        ModuleFullTaskConfigService.replace(self.product.id, [])
        self.assertFalse(Tasks.objects.filter(id=task.id).exists())

    def test_parent_rule_excludes_submitted_child(self):
        result = ModuleFullTaskConfigService.replace(
            self.product.id,
            [self.row(module_id=self.parent.id), self.row(case_types=[1])],
        )

        self.assertTrue(Tasks.objects.filter(module=self.parent).exists())
        self.assertFalse(Tasks.objects.filter(module=self.module).exists())
        self.assertEqual(result['create_count'], 1)
        self.assertEqual(result['disabled_count'], 0)

    def test_parent_rule_deletes_existing_child(self):
        ModuleFullTaskConfigService.replace(self.product.id, [self.row()])

        result = ModuleFullTaskConfigService.replace(
            self.product.id,
            [self.row(module_id=self.parent.id)],
        )

        self.assertFalse(Tasks.objects.filter(module=self.module).exists())
        self.assertEqual(result['delete_count'], 1)
        self.assertEqual(result['disabled_count'], 0)

    def test_parent_rule_deletes_child_even_when_parent_is_disabled(self):
        ModuleFullTaskConfigService.replace(self.product.id, [self.row()])

        ModuleFullTaskConfigService.replace(
            self.product.id,
            [self.row(module_id=self.parent.id, status=0)],
        )

        self.assertTrue(Tasks.objects.filter(module=self.parent, status=0).exists())
        self.assertFalse(Tasks.objects.filter(module=self.module).exists())

    def test_create_rows_keeps_existing_tasks_and_removes_covered_children(self):
        ModuleFullTaskConfigService.create_rows(self.product.id, [self.row()])

        result = ModuleFullTaskConfigService.create_rows(
            self.product.id,
            [self.row(module_id=self.parent.id)],
            update_user_id=self.owner.id,
        )

        self.assertEqual(result['create_count'], 1)
        self.assertEqual(result['delete_count'], 1)
        self.assertTrue(Tasks.objects.filter(module=self.parent).exists())
        self.assertFalse(Tasks.objects.filter(module=self.module).exists())

    def test_update_row_updates_one_task_without_replacing_others(self):
        sibling = ProductModule.objects.create(
            project_product=self.product,
            name='订单创建',
            level=1,
        )
        first = ModuleFullTaskConfigService.create_rows(self.product.id, [self.row()])['items'][0]
        ModuleFullTaskConfigService.create_rows(
            self.product.id,
            [self.row(module_id=sibling.id, name='订单创建任务')],
        )

        result = ModuleFullTaskConfigService.update_row(
            first['task_id'],
            self.row(name='已实时修改'),
            update_user_id=self.owner.id,
        )

        self.assertEqual(result['item']['name'], '已实时修改')
        self.assertEqual(Tasks.objects.count(), 2)

    def test_delete_row_only_deletes_selected_task_group(self):
        task_id = ModuleFullTaskConfigService.create_rows(
            self.product.id,
            [self.row()],
        )['items'][0]['task_id']

        ModuleFullTaskConfigService.delete_row(task_id)

        self.assertFalse(Tasks.objects.filter(id=task_id).exists())

    def test_matrix_uses_task_module_field_for_display(self):
        ModuleFullTaskConfigService.create_rows(self.product.id, [self.row()])

        item = ModuleFullTaskConfigService.matrix(self.product.id)['items'][0]

        self.assertEqual(item['module']['id'], self.module.id)
        self.assertEqual(item['module']['name'], self.module.name)
        self.assertEqual(item['module']['full_path'], '订单中心/订单查询')

    def test_regular_create_rejects_module_scope(self):
        serializer = TasksSerializers(data={
            'project_product': self.product.id,
            'module': self.module.id,
            'test_envs': [EnvironmentEnum.TEST.value],
            'case_types': [0],
            'execution_scenes': [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value],
            'execution_scope': AutomationExecutionScopeEnum.MODULE.value,
            'name': '不允许直接创建的模块全量任务',
            'case_people': self.owner.id,
            'timing_strategies': [self.strategy.id],
        })

        with self.assertRaises(TaskCenterError):
            serializer.is_valid()

    def test_regular_create_allows_full_product_scope(self):
        serializer = TasksSerializers(data={
            'project_product': self.product.id,
            'module': None,
            'test_envs': [EnvironmentEnum.TEST.value],
            'case_types': [0],
            'execution_scenes': [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value],
            'execution_scope': AutomationExecutionScopeEnum.FULL_PRODUCT.value,
            'name': '普通入口创建产品全量任务',
            'case_people': self.owner.id,
            'timing_strategies': [self.strategy.id],
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        task = serializer.save()
        self.assertEqual(task.execution_scope, AutomationExecutionScopeEnum.FULL_PRODUCT.value)

    def test_full_product_task_can_be_updated_and_deleted_from_regular_entry(self):
        task = Tasks.objects.create(
            project_product=self.product,
            module=None,
            test_envs=[EnvironmentEnum.TEST.value],
            case_types=[0],
            execution_scenes=[AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value],
            execution_scope=AutomationExecutionScopeEnum.FULL_PRODUCT.value,
            name='待编辑产品全量任务',
            case_people=self.owner,
            status=0,
        )
        task.timing_strategies.add(self.strategy)
        serializer = TasksSerializers(
            task,
            data={'name': '已编辑产品全量任务'},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        task.delete()
        self.assertFalse(Tasks.objects.filter(id=task.id).exists())
