from django.test import TestCase

from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.models import ScheduledTaskGroup, ScheduledTaskGroupModule, Tasks, TimeTasks
from src.apps.task_center.services.scheduling.task_group import ScheduledTaskGroupService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import ProductModule, NoticeGroup, Project, ProjectProduct
from src.apps.user.models import User


class ScheduledTaskGroupServiceTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='任务组测试项目')
        self.product = ProjectProduct.objects.create(project=self.project, name='WEB端')
        self.parent = ProductModule.objects.create(
            project_product=self.product,
            name='订单管理',
            level=1,
        )
        self.first = ProductModule.objects.create(
            project_product=self.product,
            parent=self.parent,
            name='订单查询',
            level=2,
        )
        self.second = ProductModule.objects.create(
            project_product=self.product,
            parent=self.parent,
            name='订单创建',
            level=2,
        )
        self.owner = User.objects.create(
            name='任务组负责人',
            username='scheduled_task_group_owner',
            password='pwd',
        )
        self.strategy = TimeTasks.objects.create(name='每天18点', cron='0 18 * * *')

    def payload(self, **overrides):
        data = {
            'project_product_id': self.product.id,
            'name': '测试回归',
            'module_ids': [self.first.id],
            'timing_strategies': [self.strategy.id],
            'test_envs': [EnvironmentEnum.TEST.value],
            'case_types': [1],
            'execution_scenes': [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value],
            'case_people': self.owner.id,
            'status': 1,
            'is_notice': 0,
            'fail_notice': 0,
            'notice_group': None,
            'api_concurrency_limit': None,
            'task_name_template': '【${{任务组名称}}】${{模块名称}}',
        }
        data.update(overrides)
        return data

    def test_create_materializes_one_module_task_per_member(self):
        result = ScheduledTaskGroupService.create(self.payload(), self.owner.id)

        group = ScheduledTaskGroup.objects.get()
        task = Tasks.objects.get()
        member = ScheduledTaskGroupModule.objects.get()
        self.assertEqual(result['create_count'], 1)
        self.assertEqual(task.task_group_id, group.id)
        self.assertEqual(task.module_id, self.first.id)
        self.assertEqual(task.execution_scope, 'module')
        self.assertEqual(member.task_id, task.id)
        self.assertEqual(task.name, '【测试回归】订单查询')

    def test_group_does_not_manage_child_api_concurrency(self):
        result = ScheduledTaskGroupService.create(
            self.payload(api_concurrency_limit=2),
            self.owner.id,
        )
        group = ScheduledTaskGroup.objects.get()
        task = Tasks.objects.get()
        self.assertNotIn('api_concurrency_limit', result['item'])
        self.assertIsNone(task.api_concurrency_limit)

        task.api_concurrency_limit = 5
        task.save(update_fields=['api_concurrency_limit'])
        result = ScheduledTaskGroupService.update(
            group.id,
            self.payload(api_concurrency_limit=2),
            self.owner.id,
        )

        group.refresh_from_db()
        task.refresh_from_db()
        self.assertNotIn('api_concurrency_limit', result['item'])
        self.assertEqual(task.api_concurrency_limit, 5)

    def test_group_is_the_source_of_child_task_notice_config(self):
        from src.apps.test_center.services.test_suite.send_notice import SendNotice

        notice_group = NoticeGroup.objects.create(
            project=self.project,
            name='任务组通知',
        )
        ScheduledTaskGroupService.create(
            self.payload(is_notice=1, fail_notice=1, notice_group=notice_group.id),
            self.owner.id,
        )
        task = Tasks.objects.select_related('task_group').get()
        Tasks.objects.filter(id=task.id).update(
            is_notice=0,
            fail_notice=0,
            notice_group=None,
        )
        task.refresh_from_db()

        self.assertEqual(
            SendNotice.task_notice_config(task),
            (1, 1, notice_group.id),
        )

    def test_legacy_task_name_template_is_normalized(self):
        result = ScheduledTaskGroupService.create(
            self.payload(task_name_template='【{group_name}】{module_full_path}'),
            self.owner.id,
        )

        group = ScheduledTaskGroup.objects.get()
        task = Tasks.objects.get()
        self.assertEqual(result['create_count'], 1)
        self.assertEqual(group.task_name_template, '【${{任务组名称}}】${{模块完整路径}}')
        self.assertEqual(task.name, '【测试回归】订单管理/订单查询')

    def test_update_adds_and_removes_members_without_deleting_tasks(self):
        ScheduledTaskGroupService.create(self.payload(), self.owner.id)
        group = ScheduledTaskGroup.objects.get()
        first_task = Tasks.objects.get(module=self.first)

        ScheduledTaskGroupService.update(
            group.id,
            self.payload(module_ids=[self.second.id]),
            self.owner.id,
        )

        first_task.refresh_from_db()
        self.assertEqual(first_task.status, 0)
        self.assertFalse(ScheduledTaskGroupModule.objects.get(module=self.first).active)
        self.assertTrue(ScheduledTaskGroupModule.objects.get(module=self.second).active)
        self.assertTrue(Tasks.objects.filter(module=self.second, task_group=group).exists())

    def test_group_status_keeps_member_pause_preference(self):
        ScheduledTaskGroupService.create(self.payload(), self.owner.id)
        group = ScheduledTaskGroup.objects.get()
        member = ScheduledTaskGroupModule.objects.get()
        ScheduledTaskGroupService.set_member_enabled(group.id, member.id, False, self.owner.id)

        ScheduledTaskGroupService.update(group.id, self.payload(status=0), self.owner.id)
        ScheduledTaskGroupService.update(group.id, self.payload(status=1), self.owner.id)

        member.refresh_from_db()
        member.task.refresh_from_db()
        self.assertFalse(member.child_enabled)
        self.assertEqual(member.task.status, 0)

    def test_parent_and_child_cannot_be_selected_in_same_group(self):
        with self.assertRaises(TaskCenterError):
            ScheduledTaskGroupService.create(
                self.payload(module_ids=[self.parent.id, self.first.id]),
                self.owner.id,
            )

    def test_delete_removes_group_members_and_generated_tasks(self):
        ScheduledTaskGroupService.create(self.payload(), self.owner.id)
        group_id = ScheduledTaskGroup.objects.get().id

        ScheduledTaskGroupService.delete(group_id)

        self.assertFalse(ScheduledTaskGroup.objects.filter(id=group_id).exists())
        self.assertFalse(ScheduledTaskGroupModule.objects.exists())
        self.assertFalse(Tasks.objects.exists())

    def test_options_can_be_limited_to_project_products(self):
        ScheduledTaskGroupService.create(self.payload(), self.owner.id)
        other_project = Project.objects.create(name='其他项目')
        other_product = ProjectProduct.objects.create(project=other_project, name='其他产品')
        ScheduledTaskGroup.objects.create(
            project_product=other_product,
            name='其他任务组',
            case_people=self.owner,
        )

        options = ScheduledTaskGroupService.options([self.product.id])

        self.assertEqual(len(options), 1)
        self.assertEqual(options[0]['title'], '测试回归')
        self.assertEqual(options[0]['project_product_id'], self.product.id)
