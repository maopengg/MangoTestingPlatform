from types import SimpleNamespace

from django.test import TestCase
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import (
    ApiCase,
    ApiCaseDetailed,
    ApiCaseDetailedParameter,
    ApiInfo,
    ApiInfoHttpConfig,
)
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
from src.apps.auto_ui.models import UiCase
from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.models import Tasks, TasksDetails, TimeTasks
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.task_center.services.execution.run_tasks import RunTasks
from src.apps.task_center.services.selection.api_case_binding import ApiCaseTaskBindingService
from src.apps.task_center.services.selection.case_binding import TaskCaseBindingService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import (
    ProductModule,
    Project,
    ProjectProduct,
    TestSuiteDetails,
)
from src.apps.test_center.services.test_suite.retry import TestSuiteRetryService
from src.apps.user.models import User


class ApiCaseTaskBindingServiceTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='定时任务版本测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='开放平台')
        self.module = ProductModule.objects.create(project_product=self.product, name='订单模块')
        self.owner = User.objects.create(
            name='任务负责人',
            username='task_case_version_owner',
            password='pwd',
        )
        self.api_info = ApiInfo.objects.create(
            project_product=self.product,
            module=self.module,
            name='创建订单',
            url='/open-apis/contracts',
        )
        ApiInfoHttpConfig.objects.create(
            api_info=self.api_info,
            url='/open-apis/contracts',
            method=1,
            headers={},
        )
        api_revision = ApiInfoRevisionService.record_current(self.api_info.id, source='test')
        ApiInfoRevisionService.publish(
            self.api_info.id, api_revision.id, publisher_id=self.owner.id,
        )
        self.api_case = ApiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='线上稳定用例',
            case_people=self.owner,
            case_flow='1',
            parametrize=[{
                'name': '线上参数',
                'parametrize': [{'key': 'environment', 'value': 'prod'}],
            }],
        )
        self.step = ApiCaseDetailed.objects.create(
            case=self.api_case,
            api_info=self.api_info,
            case_sort=1,
        )
        ApiCaseDetailedParameter.objects.create(
            case_detailed=self.step,
            name='创建成功',
            body_config={'json': {'name': '${contract_name}'}},
        )
        self.strategy = TimeTasks.objects.create(name='每天执行', cron='0 0 * * *')
        self.task = Tasks.objects.create(
            project_product=self.product,
            module=self.module,
            test_envs=[1],
            name='线上回归',
            case_people=self.owner,
        )
        self.task.timing_strategies.add(self.strategy)

    def publish_current(self):
        revision = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision.id,
            publisher_id=self.owner.id,
        )
        return revision, release

    def test_new_api_case_binding_rejects_unpublished_case(self):
        with self.assertRaises(AutoApiError):
            ApiCaseTaskBindingService.bind_current_published(
                task_id=self.task.id,
                case_id=self.api_case.id,
                update_user_id=self.owner.id,
            )

        self.assertFalse(TasksDetails.objects.exists())

    def test_reverse_dynamic_match_uses_the_same_module_scene_and_environment_rules(self):
        self.api_case.scenario_tags = [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value]
        self.api_case.save(update_fields=['scenario_tags'])
        self.publish_current()
        self.task.execution_scope = AutomationExecutionScopeEnum.MODULE.value
        self.task.test_envs = [EnvironmentEnum.TEST.value]
        self.task.case_types = [TestCaseTypeEnum.API.value]
        self.task.execution_scenes = [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value]
        self.task.save(update_fields=[
            'execution_scope',
            'test_envs',
            'case_types',
            'execution_scenes',
        ])

        matched_environments = (
            ScheduledTaskCaseSelectionService.matching_environments_for_api_case(
                self.task,
                self.api_case,
                is_published=True,
            )
        )
        forward_selected_ids = [
            item.case_id
            for item in ScheduledTaskCaseSelectionService.select_task(self.task)
            if item.case_type == TestCaseTypeEnum.API.value
        ]

        self.assertEqual(matched_environments, [EnvironmentEnum.TEST.value])
        self.assertIn(self.api_case.id, forward_selected_ids)

    def test_reverse_dynamic_match_excludes_case_only_scenarios(self):
        self.api_case.scenario_tags = [
            AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
            ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value,
        ]
        self.api_case.save(update_fields=['scenario_tags'])
        self.publish_current()
        self.task.execution_scope = AutomationExecutionScopeEnum.FULL_PRODUCT.value
        self.task.module = None
        self.task.test_envs = [EnvironmentEnum.TEST.value]
        self.task.case_types = [TestCaseTypeEnum.API.value]
        self.task.execution_scenes = [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value]
        self.task.save(update_fields=[
            'execution_scope',
            'module',
            'test_envs',
            'case_types',
            'execution_scenes',
        ])

        matched_environments = (
            ScheduledTaskCaseSelectionService.matching_environments_for_api_case(
                self.task,
                self.api_case,
                is_published=True,
            )
        )
        forward_selected_ids = [
            item.case_id
            for item in ScheduledTaskCaseSelectionService.select_task(self.task)
            if item.case_type == TestCaseTypeEnum.API.value
        ]

        self.assertEqual(matched_environments, [])
        self.assertNotIn(self.api_case.id, forward_selected_ids)

    def test_new_api_case_binding_pins_current_release_and_checksum(self):
        revision_v1, release_v1 = self.publish_current()

        detail, created = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )

        self.assertTrue(created)
        self.assertEqual(detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(detail.api_case_release_id, release_v1.id)
        self.assertEqual(
            detail.version_policy,
            ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED,
        )
        self.assertEqual(detail.bound_checksum, revision_v1.checksum)
        self.assertEqual(detail.update_user_id, self.owner.id)
        self.assertIsNotNone(detail.bound_at)

    def test_existing_binding_does_not_follow_later_release(self):
        revision_v1, release_v1 = self.publish_current()
        detail, _ = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )

        self.api_case.name = '测试环境草稿 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )
        same_detail, created = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )

        self.assertFalse(created)
        self.assertEqual(same_detail.id, detail.id)
        self.assertEqual(same_detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(same_detail.api_case_release_id, release_v1.id)
        self.assertNotEqual(same_detail.api_case_revision_id, revision_v2.id)
        self.assertNotEqual(same_detail.api_case_release_id, release_v2.id)

    def test_explicit_release_binding_can_pin_history_and_upgrade_only_on_request(self):
        revision_v1, release_v1 = self.publish_current()
        self.api_case.name = '线上稳定用例 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )

        detail, created = ApiCaseTaskBindingService.bind_release(
            task_id=self.task.id,
            case_id=self.api_case.id,
            release_id=release_v1.id,
            update_user_id=self.owner.id,
        )

        self.assertTrue(created)
        self.assertEqual(detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(detail.api_case_release_id, release_v1.id)

        upgraded, created = ApiCaseTaskBindingService.bind_release(
            task_id=self.task.id,
            case_id=self.api_case.id,
            release_id=release_v2.id,
            update_user_id=self.owner.id,
        )

        self.assertFalse(created)
        self.assertEqual(upgraded.id, detail.id)
        self.assertEqual(upgraded.api_case_revision_id, revision_v2.id)
        self.assertEqual(upgraded.api_case_release_id, release_v2.id)

    def test_deprecated_release_cannot_be_added_as_a_new_task_binding(self):
        _, release_v1 = self.publish_current()
        release_v1.status = release_v1.STATUS_DEPRECATED
        release_v1.save(update_fields=['status'])

        with self.assertRaises(AutoApiError):
            ApiCaseTaskBindingService.bind_release(
                task_id=self.task.id,
                case_id=self.api_case.id,
                release_id=release_v1.id,
                update_user_id=self.owner.id,
            )

        self.assertFalse(
            TasksDetails.objects.filter(task=self.task, api_case=self.api_case).exists()
        )

    def test_release_from_another_product_cannot_be_bound_to_task(self):
        other_project = Project.objects.create(name='其他版本项目')
        other_product = ProjectProduct.objects.create(project=other_project, name='其他开放平台')
        other_module = ProductModule.objects.create(
            project_product=other_product,
            name='其他模块',
        )
        other_case = ApiCase.objects.create(
            project_product=other_product,
            module=other_module,
            name='跨产品用例',
            case_people=self.owner,
            case_flow='1',
        )
        other_api_info = ApiInfo.objects.create(
            project_product=other_product,
            module=other_module,
            name='跨产品接口',
            url='/open-apis/other-contracts',
            method=1,
            headers={},
        )
        other_step = ApiCaseDetailed.objects.create(
            case=other_case,
            api_info=other_api_info,
            case_sort=1,
        )
        ApiCaseDetailedParameter.objects.create(
            case_detailed=other_step,
            name='跨产品有效场景',
        )
        other_revision = ApiCaseRevisionService.record_current(other_case.id, source='test')
        other_release = ApiCaseRevisionService._publish_revision(
            other_case.id,
            other_revision.id,
            publisher_id=self.owner.id,
        )

        with self.assertRaises(AutoApiError):
            ApiCaseTaskBindingService.bind_release(
                task_id=self.task.id,
                case_id=other_case.id,
                release_id=other_release.id,
                update_user_id=self.owner.id,
            )

        self.assertFalse(TasksDetails.objects.filter(task=self.task).exists())

    def test_case_from_another_module_cannot_be_bound_to_scoped_task(self):
        other_module = ProductModule.objects.create(
            project_product=self.product,
            name='结算模块',
        )
        other_case = ApiCase.objects.create(
            project_product=self.product,
            module=other_module,
            name='结算用例',
            case_people=self.owner,
            case_flow='1',
        )

        with self.assertRaises(AutoApiError):
            ApiCaseTaskBindingService.bind_current_published(
                task_id=self.task.id,
                case_id=other_case.id,
                update_user_id=self.owner.id,
            )

        self.assertFalse(TasksDetails.objects.filter(task=self.task).exists())

    def test_task_case_selector_includes_descendant_modules_and_module_path(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsViews

        category = ProductModule.objects.create(
            project_product=self.product,
            parent=self.module,
            name='权限',
            level=2,
        )
        leaf = ProductModule.objects.create(
            project_product=self.product,
            parent=category,
            name='成员权限',
            level=3,
        )
        self.api_case.module = leaf
        self.api_case.save(update_fields=['module'])
        self.task.module = category
        self.task.save(update_fields=['module'])
        self.publish_current()
        request = SimpleNamespace(query_params={
            'type': str(TestCaseTypeEnum.API.value),
            'module_id': str(category.id),
            'project_product_id': str(self.product.id),
        })

        for task_id in (None, str(self.task.id)):
            with self.subTest(task_id=task_id):
                if task_id:
                    request.query_params['task_id'] = task_id
                response = TasksDetailsViews().get_type_case_name(request)
                self.assertEqual(response.data['code'], 200)
                self.assertEqual([row['key'] for row in response.data['data']], [self.api_case.id])
                self.assertEqual(response.data['data'][0]['module'], {
                    'id': leaf.id,
                    'name': '成员权限',
                    'full_path': leaf.get_full_path(),
                })

        result = TaskCaseBindingService.bind(
            self.task.id,
            TestCaseTypeEnum.API.value,
            [self.api_case.id],
            update_user_id=self.owner.id,
        )
        self.assertEqual(result.created_ids, [self.api_case.id])
        self.assertEqual(result.module_mismatched_ids, [])
        self.assertTrue(TasksDetails.objects.filter(task=self.task, api_case=self.api_case).exists())

    def test_task_list_parent_module_includes_tasks_at_all_descendant_levels(self):
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory
        from src.apps.task_center.api.views.tasks import TasksCRUD

        category = ProductModule.objects.create(
            project_product=self.product, parent=self.module, name='权限', level=2,
        )
        leaf = ProductModule.objects.create(
            project_product=self.product, parent=category, name='成员权限', level=3,
        )
        sibling = ProductModule.objects.create(project_product=self.product, name='其他模块')
        category_task = Tasks.objects.create(
            project_product=self.product, module=category, name='二级模块任务', case_people=self.owner,
        )
        leaf_task = Tasks.objects.create(
            project_product=self.product, module=leaf, name='三级模块任务', case_people=self.owner,
        )
        Tasks.objects.create(
            project_product=self.product, module=sibling, name='其他模块任务', case_people=self.owner,
        )
        factory = APIRequestFactory()

        for module, expected_ids in (
                (self.module, {self.task.id, category_task.id, leaf_task.id}),
                (category, {category_task.id, leaf_task.id}),
                (leaf, {leaf_task.id}),
        ):
            with self.subTest(module_id=module.id):
                request = Request(factory.get('/system/tasks', {
                    'project_product': self.product.id,
                    'module': module.id,
                    'module__in': str(leaf.id),
                    'page': 1,
                    'pageSize': 20,
                }))
                response = TasksCRUD().get(request)
                self.assertEqual(response.data['code'], 200)
                self.assertEqual({row['id'] for row in response.data['data']}, expected_ids)
                self.assertEqual(request.query_params.get('module'), str(module.id))

        invalid_request = Request(factory.get('/system/tasks', {'module': 'invalid'}))
        self.assertEqual(TasksCRUD().get(invalid_request).data['data'], [])

    def test_task_bound_case_ids_use_one_query_and_respect_task_and_type(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsCRUD

        ui_case = UiCase.objects.create(
            project_product=self.product, module=self.module, name='UI 用例',
            case_people=self.owner, case_flow='', publication_status='published',
        )
        TasksDetails.objects.create(
            task=self.task, type=TestCaseTypeEnum.UI.value, ui_case=ui_case,
        )
        TasksDetails.objects.create(
            task=self.task, type=TestCaseTypeEnum.API.value, api_case=self.api_case,
        )
        other_task = Tasks.objects.create(
            project_product=self.product, name='其他任务', case_people=self.owner,
        )
        TasksDetails.objects.create(
            task=other_task, type=TestCaseTypeEnum.UI.value, ui_case=ui_case,
        )
        request = SimpleNamespace(query_params={
            'task_id': str(self.task.id),
            'type': str(TestCaseTypeEnum.API.value),
            'case_ids_only': '1',
        })
        with self.assertNumQueries(1):
            response = TasksDetailsCRUD().get(request)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['data'], [
            {'type': TestCaseTypeEnum.API.value, 'case_id': self.api_case.id},
        ])
        self.assertEqual(response.data['totalSize'], 1)

        request.query_params.pop('type')
        response = TasksDetailsCRUD().get(request)
        self.assertEqual(response.data['data'], [
            {'type': TestCaseTypeEnum.UI.value, 'case_id': ui_case.id},
            {'type': TestCaseTypeEnum.API.value, 'case_id': self.api_case.id},
        ])

        request.query_params['case_name'] = '不存在的用例'
        self.assertEqual(TasksDetailsCRUD().get(request).data['data'], [])

    def test_tasks_details_post_reports_new_and_already_bound_ui_cases(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsCRUD

        ui_cases = [UiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name=f'已发布 UI 用例 {index}',
            case_people=self.owner,
            case_flow='',
            publication_status='published',
        ) for index in range(2)]
        TasksDetails.objects.create(
            task=self.task, type=TestCaseTypeEnum.UI.value, ui_case=ui_cases[0],
        )
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.UI.value,
                'task': self.task.id,
                'ui_case': [case.id for case in ui_cases],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsCRUD().post(request)

        self.assertEqual(response.data['code'], 200)
        self.assertEqual(response.data['data'], {
            'created_ids': [ui_cases[1].id],
            'updated_ids': [],
            'skipped_ids': [ui_cases[0].id],
            'created_count': 1,
            'updated_count': 0,
            'skipped_count': 1,
        })
        self.assertEqual(TasksDetails.objects.filter(task=self.task).count(), 2)

    def test_task_without_module_allows_cases_from_any_module_in_same_product(self):
        other_module = ProductModule.objects.create(
            project_product=self.product,
            name='结算模块',
        )
        other_case = ApiCase.objects.create(
            project_product=self.product,
            module=other_module,
            name='结算用例',
            case_people=self.owner,
            case_flow='1',
        )
        self.task.module = None
        self.task.save(update_fields=['module'])

        result = TaskCaseBindingService.inspect_bind(
            self.task.id,
            TestCaseTypeEnum.API.value,
            [other_case.id],
        )

        self.assertEqual(result.created_ids, [other_case.id])
        self.assertEqual(result.product_mismatched_ids, [])
        self.assertEqual(result.module_mismatched_ids, [])

    def test_task_case_types_reject_other_case_types(self):
        self.task.case_types = [TestCaseTypeEnum.API.value]
        self.task.save(update_fields=['case_types'])

        result = TaskCaseBindingService.inspect_bind(
            self.task.id,
            TestCaseTypeEnum.UI.value,
            [self.api_case.id],
        )

        self.assertEqual(result.type_mismatched_ids, [self.api_case.id])
        self.assertEqual(result.mismatched_ids, [self.api_case.id])
        self.assertEqual(result.created_ids, [])

    def test_task_without_case_types_allows_all_supported_types(self):
        self.assertEqual(self.task.case_types, [])

        result = TaskCaseBindingService.inspect_bind(
            self.task.id,
            TestCaseTypeEnum.API.value,
            [self.api_case.id],
        )

        self.assertEqual(result.type_mismatched_ids, [])
        self.assertEqual(result.created_ids, [self.api_case.id])

    def test_ui_case_must_be_published_before_binding_to_task(self):
        ui_case = UiCase.objects.create(
            project_product=self.product,
            module=self.module,
            name='UI 发布状态校验用例',
            case_people=self.owner,
            case_flow='',
        )

        unpublished_result = TaskCaseBindingService.bind(
            self.task.id,
            TestCaseTypeEnum.UI.value,
            [ui_case.id],
            update_user_id=self.owner.id,
        )

        self.assertEqual(unpublished_result.unpublished_ids, [ui_case.id])
        self.assertEqual(unpublished_result.created_ids, [])
        self.assertFalse(TasksDetails.objects.filter(ui_case=ui_case).exists())

        ui_case.publication_status = 'published'
        ui_case.save(update_fields=['publication_status'])
        published_result = TaskCaseBindingService.bind(
            self.task.id,
            TestCaseTypeEnum.UI.value,
            [ui_case.id],
            update_user_id=self.owner.id,
        )

        self.assertEqual(published_result.unpublished_ids, [])
        self.assertEqual(published_result.created_ids, [ui_case.id])
        self.assertTrue(TasksDetails.objects.filter(ui_case=ui_case).exists())

        ui_case.publication_status = 'unpublished'
        ui_case.save(update_fields=['publication_status'])
        self.assertFalse(TaskCaseBindingService.executable_details(self.task).exists())

    def test_manual_execution_uses_the_explicit_binding_list(self):
        self.publish_current()
        detail, _ = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )
        other_module = ProductModule.objects.create(
            project_product=self.product,
            name='修改后的任务模块',
        )
        self.task.module = other_module
        self.task.case_types = [TestCaseTypeEnum.UI.value]
        self.task.test_envs = [EnvironmentEnum.PRO.value]
        self.task.execution_scenes = [AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value]
        self.task.save(update_fields=['module', 'case_types', 'test_envs', 'execution_scenes'])

        executable_ids = list(
            TaskCaseBindingService.executable_details(self.task).values_list('id', flat=True)
        )

        self.assertEqual(executable_ids, [detail.id])

    def test_batch_set_cases_rejects_case_from_another_module(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsViews

        other_module = ProductModule.objects.create(
            project_product=self.product,
            name='结算模块',
        )
        other_case = ApiCase.objects.create(
            project_product=self.product,
            module=other_module,
            name='结算用例',
            case_people=self.owner,
            case_flow='1',
        )
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.API.value,
                'scheduled_tasks_id': self.task.id,
                'case_id_list': [other_case.id],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsViews().batch_set_cases(request)

        self.assertEqual(response.data['code'], 300)
        self.assertIn('已限定模块', response.data['msg'])
        self.assertFalse(TasksDetails.objects.filter(task=self.task).exists())

    def test_batch_set_cases_rejects_case_type_mismatch(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsViews

        self.task.case_types = [TestCaseTypeEnum.UI.value]
        self.task.save(update_fields=['case_types'])
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.API.value,
                'scheduled_tasks_id': self.task.id,
                'case_id_list': [self.api_case.id],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsViews().batch_set_cases(request)

        self.assertEqual(response.data['code'], 300)
        self.assertIn('已限定用例类型', response.data['msg'])
        self.assertFalse(TasksDetails.objects.filter(task=self.task).exists())

    def test_task_name_options_filter_product_and_show_module_prefix(self):
        from src.apps.task_center.api.views.tasks import TasksViews

        same_product_other_module = ProductModule.objects.create(
            project_product=self.product,
            name='同产品其他模块',
        )
        same_product_task = Tasks.objects.create(
            project_product=self.product,
            module=same_product_other_module,
            test_envs=[1],
            name='同产品其他任务',
            case_people=self.owner,
        )
        same_product_task.timing_strategies.add(self.strategy)
        other_project = Project.objects.create(name='其他任务项目')
        other_product = ProjectProduct.objects.create(project=other_project, name='其他产品')
        other_module = ProductModule.objects.create(
            project_product=other_product,
            name='其他模块',
        )
        other_task = Tasks.objects.create(
            project_product=other_product,
            module=other_module,
            test_envs=[1],
            name='其他任务',
            case_people=self.owner,
        )
        other_task.timing_strategies.add(self.strategy)
        request = SimpleNamespace(
            query_params={
                'project_product_id': str(self.product.id),
                'module_id': str(self.module.id),
            },
        )

        response = TasksViews().get_id_name(request)

        self.assertEqual(response.data['code'], 200)
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['key'], self.task.id)
        self.assertEqual(response.data['data'][0]['title'], '订单模块/线上回归')

    def test_task_name_options_include_descendant_modules_for_selected_category(self):
        from src.apps.task_center.api.views.tasks import TasksViews

        level_one = ProductModule.objects.create(
            project_product=self.product,
            name='业务中心',
            level=1,
        )
        level_two = ProductModule.objects.create(
            project_product=self.product,
            parent=level_one,
            name='结算分类',
            level=2,
        )
        level_three = ProductModule.objects.create(
            project_product=self.product,
            parent=level_two,
            name='账单模块',
            level=3,
        )
        descendant_task = Tasks.objects.create(
            project_product=self.product,
            module=level_three,
            test_envs=[1],
            name='账单回归',
            case_people=self.owner,
        )
        descendant_task.timing_strategies.add(self.strategy)
        request = SimpleNamespace(
            query_params={
                'project_product_id': str(self.product.id),
                'module_id': str(level_one.id),
            },
        )

        response = TasksViews().get_id_name(request)

        self.assertEqual(response.data['code'], 200)
        self.assertEqual([item['key'] for item in response.data['data']], [descendant_task.id])
        self.assertEqual(response.data['data'][0]['title'], '账单模块/账单回归')

    def test_add_tasks_reads_name_parameters_and_case_sum_from_pinned_revision(self):
        revision_v1, release_v1 = self.publish_current()
        task_detail, _ = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )

        self.api_case.name = '当前态不应被读取'
        self.api_case.parametrize = [{
            'name': '测试参数',
            'parametrize': [{'key': 'environment', 'value': 'test'}],
        }]
        self.api_case.save(update_fields=['name', 'parametrize', 'update_time'])
        ApiCaseDetailedParameter.objects.create(
            case_detailed=self.step,
            name='V2 新增步骤',
        )

        add_tasks = AddTasks(
            project_product=self.product.id,
            test_env=1,
            is_notice=0,
            user_id=self.owner.id,
            tasks_id=self.task.id,
            module_id=self.module.id,
        )
        add_tasks.add_test_suite_details(
            self.api_case.id,
            TestCaseTypeEnum.API,
            api_case_revision_id=task_detail.api_case_revision_id,
            api_case_release_id=task_detail.api_case_release_id,
            bound_checksum=task_detail.bound_checksum,
        )

        suite_detail = TestSuiteDetails.objects.get(test_suite_id=add_tasks.test_suite_id)
        self.assertEqual(suite_detail.case_name, '线上稳定用例 - 线上参数')
        self.assertEqual(
            suite_detail.parametrize,
            [{'key': 'environment', 'value': 'prod'}],
        )
        self.assertEqual(suite_detail.case_sum, 1)
        self.assertEqual(suite_detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(suite_detail.api_case_release_id, release_v1.id)
        self.assertEqual(suite_detail.config_checksum, revision_v1.checksum)
        self.assertEqual(task_detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(task_detail.api_case_release_id, release_v1.id)

    def test_scheduled_distribution_resolves_current_published_release(self):
        revision_v1, release_v1 = self.publish_current()
        task_detail, _ = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )

        self.api_case.name = 'V2 当前态名称'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )

        RunTasks.distribute(self.task, user_id=self.owner.id)

        suite_detail = TestSuiteDetails.objects.get(test_suite__tasks=self.task)
        self.assertEqual(suite_detail.case_name, 'V2 当前态名称 - 线上参数')
        self.assertEqual(suite_detail.api_case_revision_id, revision_v2.id)
        self.assertEqual(suite_detail.api_case_release_id, release_v2.id)
        self.assertEqual(suite_detail.config_checksum, revision_v2.checksum)
        task_detail.refresh_from_db()
        self.assertEqual(task_detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(task_detail.api_case_release_id, release_v1.id)

    def test_scheduled_distribution_uses_current_release_without_task_binding(self):
        revision, release = self.publish_current()
        TasksDetails.objects.create(
            task=self.task,
            type=TestCaseTypeEnum.API.value,
            api_case=self.api_case,
        )

        RunTasks.distribute(self.task, user_id=self.owner.id)

        detail = TestSuiteDetails.objects.get(test_suite__tasks=self.task)
        self.assertEqual(detail.api_case_revision_id, revision.id)
        self.assertEqual(detail.api_case_release_id, release.id)

    def test_api_worker_claim_refreshes_to_latest_published_release(self):
        from src.apps.task_center.services.execution.claim import ApiTaskClaimService

        self.publish_current()
        ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )
        RunTasks.distribute(self.task, user_id=self.owner.id)
        self.api_case.name = 'Worker 领取前发布的 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )

        claimed = ApiTaskClaimService.claim()

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.case_revision_id, revision_v2.id)
        self.assertEqual(claimed.case_release_id, release_v2.id)
        self.assertEqual(claimed.config_checksum, revision_v2.checksum)
        detail = TestSuiteDetails.objects.get(id=claimed.test_suite_details)
        self.assertEqual(detail.api_case_revision_id, revision_v2.id)
        self.assertEqual(detail.api_case_release_id, release_v2.id)

    def test_schedule_dispatch_service_uses_current_published_release(self):
        from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService

        self.publish_current()
        ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )
        self.api_case.name = 'V2 当前草稿'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )

        suite_id = ScheduleDispatchService.create_test_suite(self.task)

        detail = TestSuiteDetails.objects.get(test_suite_id=suite_id)
        self.assertEqual(detail.case_name, 'V2 当前草稿 - 线上参数')
        self.assertEqual(detail.api_case_revision_id, revision_v2.id)
        self.assertEqual(detail.api_case_release_id, release_v2.id)

    def test_report_detail_retry_refreshes_to_current_published_release(self):
        self.publish_current()
        ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )
        RunTasks.distribute(self.task, user_id=self.owner.id)
        detail = TestSuiteDetails.objects.get(test_suite__tasks=self.task)
        detail.status = TaskEnum.FAIL.value
        detail.save(update_fields=['status'])

        self.api_case.name = '报告重试使用 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )

        TestSuiteRetryService.retry_detail(detail.id)

        detail.refresh_from_db()
        self.assertEqual(detail.api_case_revision_id, revision_v2.id)
        self.assertEqual(detail.api_case_release_id, release_v2.id)
        self.assertEqual(detail.config_checksum, revision_v2.checksum)
        self.assertEqual(detail.status, TaskEnum.STAY_BEGIN.value)

    def test_add_tasks_rejects_release_that_does_not_match_revision(self):
        revision_v1, _ = self.publish_current()
        self.api_case.name = 'V2 当前态名称'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )
        add_tasks = AddTasks(
            project_product=self.product.id,
            test_env=1,
            is_notice=0,
            user_id=self.owner.id,
            tasks_id=self.task.id,
            module_id=self.module.id,
        )

        with self.assertRaises(AutoApiError):
            add_tasks.add_test_suite_details(
                self.api_case.id,
                TestCaseTypeEnum.API,
                api_case_revision_id=revision_v1.id,
                api_case_release_id=release_v2.id,
                bound_checksum=revision_v1.checksum,
            )

        self.assertFalse(TestSuiteDetails.objects.filter(test_suite_id=add_tasks.test_suite_id).exists())

    def test_tasks_details_post_defaults_to_published_policy(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsCRUD

        revision, release = self.publish_current()
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.API.value,
                'task': self.task.id,
                'api_case': [self.api_case.id],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsCRUD().post(request)

        self.assertEqual(response.data['code'], 200)
        detail = TasksDetails.objects.get(task=self.task, api_case=self.api_case)
        self.assertEqual(detail.api_case_revision_id, revision.id)
        self.assertEqual(detail.api_case_release_id, release.id)
        self.assertEqual(detail.bound_checksum, revision.checksum)

    def test_legacy_unpublished_policy_is_normalized_to_current_published(self):
        from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService

        revision, release = self.publish_current()
        detail, created = ApiCaseTaskBindingService.bind_version_status(
            task_id=self.task.id,
            case_id=self.api_case.id,
            version_policy=ApiCaseTaskBindingService.VERSION_STATUS_UNPUBLISHED,
            update_user_id=self.owner.id,
        )

        self.assertTrue(created)
        self.assertEqual(
            detail.version_policy,
            ApiCaseTaskBindingService.VERSION_STATUS_PUBLISHED,
        )
        self.assertEqual(detail.api_case_revision_id, revision.id)
        self.assertEqual(detail.api_case_release_id, release.id)
        suite_id = ScheduleDispatchService.create_test_suite(self.task)
        suite_detail = TestSuiteDetails.objects.get(test_suite_id=suite_id)
        self.assertEqual(suite_detail.api_case_revision_id, revision.id)
        self.assertEqual(suite_detail.api_case_release_id, release.id)
        self.assertEqual(suite_detail.config_checksum, revision.checksum)

    def test_tasks_details_post_ignores_legacy_release_and_binds_current_published(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsCRUD

        _, release_v1 = self.publish_current()
        self.api_case.name = '线上稳定用例 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        release_v2 = ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.API.value,
                'task': self.task.id,
                'api_case_items': [{
                    'case_id': self.api_case.id,
                    'case_release_id': release_v1.id,
                    'version_policy': ApiCaseTaskBindingService.VERSION_STATUS_UNPUBLISHED,
                }],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsCRUD().post(request)

        self.assertEqual(response.data['code'], 200)
        detail = TasksDetails.objects.get(task=self.task, api_case=self.api_case)
        self.assertEqual(detail.api_case_revision_id, revision_v2.id)
        self.assertEqual(detail.api_case_release_id, release_v2.id)

    def test_tasks_details_read_model_exposes_the_bound_case_version(self):
        from src.apps.task_center.api.serializers.tasks_details import TasksDetailsSerializersC

        revision, release = self.publish_current()
        detail, _ = ApiCaseTaskBindingService.bind_current_published(
            task_id=self.task.id,
            case_id=self.api_case.id,
            update_user_id=self.owner.id,
        )

        data = TasksDetailsSerializersC(instance=detail).data

        self.assertEqual(data['api_case_version_label'], release.version_label)
        self.assertEqual(data['api_case_revision_no'], revision.revision_no)
        self.assertEqual(data['update_user_name'], self.owner.name)

    def test_batch_set_cases_pins_current_published_revision(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsViews

        revision, release = self.publish_current()
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.API.value,
                'scheduled_tasks_id': self.task.id,
                'case_id_list': [self.api_case.id],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsViews().batch_set_cases(request)

        self.assertEqual(response.data['code'], 200)
        detail = TasksDetails.objects.get(task=self.task, api_case=self.api_case)
        self.assertEqual(detail.api_case_revision_id, revision.id)
        self.assertEqual(detail.api_case_release_id, release.id)

    def test_batch_set_cases_accepts_explicit_release_items(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsViews

        revision_v1, release_v1 = self.publish_current()
        self.api_case.name = '线上稳定用例 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        ApiCaseRevisionService._publish_revision(
            self.api_case.id,
            revision_v2.id,
            publisher_id=self.owner.id,
        )
        request = SimpleNamespace(
            data={
                'type': TestCaseTypeEnum.API.value,
                'scheduled_tasks_id': self.task.id,
                'case_items': [{
                    'case_id': self.api_case.id,
                    'case_release_id': release_v1.id,
                }],
            },
            user={'id': self.owner.id},
        )

        response = TasksDetailsViews().batch_set_cases(request)

        self.assertEqual(response.data['code'], 200)
        detail = TasksDetails.objects.get(task=self.task, api_case=self.api_case)
        self.assertEqual(detail.api_case_revision_id, revision_v1.id)
        self.assertEqual(detail.api_case_release_id, release_v1.id)

    def test_task_case_selector_exposes_publication_state_and_release_options(self):
        from src.apps.task_center.api.views.tasks_details import TasksDetailsViews

        revision_v1, release_v1 = self.publish_current()
        self.api_case.name = '未发布草稿 V2'
        self.api_case.save(update_fields=['name', 'update_time'])
        revision_v2 = ApiCaseRevisionService.record_current(self.api_case.id, source='test')
        request = SimpleNamespace(query_params={
            'type': str(TestCaseTypeEnum.API.value),
            'project_product_id': str(self.product.id),
        })

        response = TasksDetailsViews().get_type_case_name(request)

        self.assertEqual(response.data['code'], 200)
        row = response.data['data'][0]
        self.assertEqual(row['key'], self.api_case.id)
        self.assertEqual(row['publication_status'], 'published')
        self.assertEqual(row['current_revision_id'], revision_v2.id)
        self.assertEqual(row['published_release_id'], release_v1.id)
        self.assertEqual(row['published_version_label'], 'V1')
        self.assertEqual(row['release_options'], [{
            'release_id': release_v1.id,
            'revision_id': revision_v1.id,
            'revision_no': revision_v1.revision_no,
            'version_label': release_v1.version_label,
            'status': release_v1.status,
            'is_current': True,
        }])

    def test_mcp_scheduled_task_binding_pins_current_published_revision(self):
        from src.interfaces.mcp.tools.scheduled_task.task import _bind_case_ids

        revision, release = self.publish_current()
        created, updated, skipped, missing = _bind_case_ids(
            scheduled_task_id=self.task.id,
            case_ids=[self.api_case.id],
            model=ApiCase,
            case_field='api_case_id',
            case_type=TestCaseTypeEnum.API.value,
        )

        self.assertEqual(created, [self.api_case.id])
        self.assertEqual(updated, [])
        self.assertEqual(skipped, [])
        self.assertEqual(missing, [])
        detail = TasksDetails.objects.get(task=self.task, api_case=self.api_case)
        self.assertEqual(detail.api_case_revision_id, revision.id)
        self.assertEqual(detail.api_case_release_id, release.id)

    def test_pinned_binding_can_continue_to_run_deprecated_release(self):
        revision_v1, release_v1 = self.publish_current()
        release_v1.status = release_v1.STATUS_DEPRECATED
        release_v1.save(update_fields=['status'])
        add_tasks = AddTasks(
            project_product=self.product.id,
            test_env=1,
            is_notice=0,
            user_id=self.owner.id,
            tasks_id=self.task.id,
            module_id=self.module.id,
        )

        add_tasks.add_test_suite_details(
            self.api_case.id,
            TestCaseTypeEnum.API,
            api_case_revision_id=revision_v1.id,
            api_case_release_id=release_v1.id,
            bound_checksum=revision_v1.checksum,
        )

        suite_detail = TestSuiteDetails.objects.get(test_suite_id=add_tasks.test_suite_id)
        self.assertEqual(suite_detail.api_case_release_id, release_v1.id)
        selection = ApiCaseRevisionService.resolve_revision(
            self.api_case.id,
            revision_v1.id,
            release_id=release_v1.id,
        )
        self.assertEqual(selection.case_revision_id, revision_v1.id)
        self.assertEqual(selection.case_release_id, release_v1.id)

    def test_pinned_binding_rejects_retired_release(self):
        revision_v1, release_v1 = self.publish_current()
        release_v1.status = release_v1.STATUS_RETIRED
        release_v1.save(update_fields=['status'])
        add_tasks = AddTasks(
            project_product=self.product.id,
            test_env=1,
            is_notice=0,
            user_id=self.owner.id,
            tasks_id=self.task.id,
            module_id=self.module.id,
        )

        with self.assertRaises(AutoApiError):
            add_tasks.add_test_suite_details(
                self.api_case.id,
                TestCaseTypeEnum.API,
                api_case_revision_id=revision_v1.id,
                api_case_release_id=release_v1.id,
                bound_checksum=revision_v1.checksum,
            )

        self.assertFalse(TestSuiteDetails.objects.filter(test_suite_id=add_tasks.test_suite_id).exists())
