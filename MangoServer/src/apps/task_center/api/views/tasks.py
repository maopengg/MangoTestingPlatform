# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.task_center.api.serializers.tasks import TasksSerializers, TasksSerializersC
from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum
from src.apps.task_center.exceptions import (
    TASK_SCHEDULE_NOT_FOUND,
    SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED,
    SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID,
    TaskCenterError,
)
from src.apps.task_center.models import Tasks
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.task_center.services.selection.module_full_config import ModuleFullTaskConfigService
from src.apps.task_center.services.selection.recent_results import TaskRecentResultService
from src.apps.test_center.services.diagnostic_markdown import DiagnosticMarkdownService
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.middleware.auth import JwtQueryParamsAuthentication
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0035,
    RESPONSE_MSG_0099,
    RESPONSE_MSG_0100,
    RESPONSE_MSG_0210,
    RESPONSE_MSG_0282,
)


class TasksCRUD(ModelCRUD):
    model = Tasks
    queryset = Tasks.objects.all()
    serializer_class = TasksSerializersC
    serializer = TasksSerializers
    page_permission_key = 'timing.tasks'
    not_matching_str = [*ModelCRUD.not_matching_str, 'is_notice', 'task_group']

    def validate_business_module(self, data: dict, instance=None):
        # 定时任务允许选择一级、二级或三级模块，归属关系由 TasksSerializers 统一校验。
        return None

    @error_response('system')
    def get(self, request: Request):
        """JSON 多选字段按“任一命中”查询。"""
        original_query = request._request.GET
        query = original_query.copy()
        module_id = query.get('module')
        if module_id not in (None, ''):
            try:
                module_ids = ProductModuleService.module_scope_ids(int(module_id))
            except (TypeError, ValueError):
                module_ids = []
            query.pop('module', None)
            query.setlist('module__in', [str(item) for item in module_ids] or ['-1'])
        raw_values = query.getlist('case_types') + query.getlist('case_types__in')
        values = ScheduledTaskCaseSelectionService.normalize_case_types(
            [item for value in raw_values for item in str(value).split(',') if item != '']
        )
        query.pop('case_types', None)
        query.pop('case_types__in', None)
        if values:
            requested = set(values)
            matching_ids = [
                task.id
                for task in Tasks.objects.only('id', 'case_types')
                if not task.case_types or requested.intersection(task.case_types)
            ]
            query.setlist('id__in', [str(item) for item in matching_ids] or ['-1'])
        raw_scenes = query.getlist('execution_scenes') + query.getlist('execution_scenes__in')
        scenes = ScheduledTaskCaseSelectionService.normalize_execution_scenes(
            [item for value in raw_scenes for item in str(value).split(',') if item]
        ) if raw_scenes else []
        query.pop('execution_scenes', None)
        query.pop('execution_scenes__in', None)
        if scenes:
            requested_scenes = set(scenes)
            scene_matching_ids = [
                task.id
                for task in Tasks.objects.only('id', 'execution_scenes')
                if requested_scenes.intersection(
                    ScheduledTaskCaseSelectionService.task_execution_scenes(task)
                )
            ]
            existing_ids = set(query.getlist('id__in')) if query.getlist('id__in') else None
            if existing_ids is not None:
                scene_matching_ids = [item for item in scene_matching_ids if str(item) in existing_ids]
            query.setlist('id__in', [str(item) for item in scene_matching_ids] or ['-1'])
        raw_test_envs = query.getlist('test_envs') + query.getlist('test_envs__in')
        test_envs = ScheduledTaskCaseSelectionService.normalize_test_envs(
            [item for value in raw_test_envs for item in str(value).split(',') if item != '']
        ) if raw_test_envs else []
        query.pop('test_envs', None)
        query.pop('test_envs__in', None)
        if test_envs:
            query.setlist('test_envs', [str(item) for item in test_envs])
        request._request.GET = query
        try:
            return super().get(request)
        finally:
            request._request.GET = original_query


class TasksViews(ViewSet):
    model = Tasks
    serializer_class = TasksSerializers
    action_permission_map = {
        'get_id_name': 'timing.tasks',
        'execution_options': 'timing.tasks',
        'recent_results': 'timing.tasks',
        'diagnostic_markdown': 'timing.tasks',
        'selection_cases': 'timing.tasks',
        'trigger_manual': 'timing.tasks:execute',
        'module_config': 'timing.tasks',
        'save_module_config': 'timing.tasks:edit',
        'task_group': 'timing.tasks:edit',
    }

    @staticmethod
    def _has_task_scope(request: Request, task: Tasks) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        return ProjectProductScopeService.has_project_product(user, task.project_product_id)

    @staticmethod
    def _has_product_scope(request: Request, project_product_id: int) -> bool:
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        return ProjectProductScopeService.has_project_product(user, project_product_id)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def module_config(self, request: Request):
        try:
            project_product_id = int(request.query_params.get('project_product_id'))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED,
                                  error=str(error)) from error
        if not self._has_product_scope(request, project_product_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ModuleFullTaskConfigService.matrix(project_product_id),
        )

    @action(methods=['put'], detail=False)
    @error_response('system')
    def save_module_config(self, request: Request):
        try:
            project_product_id = int(request.data.get('project_product_id'))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED,
                                  error=str(error)) from error
        if not self._has_product_scope(request, project_product_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        result = ModuleFullTaskConfigService.replace(
            project_product_id,
            request.data.get('rows'),
            update_user_id=getattr(user, 'id', None),
        )
        return ResponseData.success(RESPONSE_MSG_0035, result)

    @action(methods=['post', 'put', 'delete'], detail=False)
    @error_response('system')
    def task_group(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        update_user_id = getattr(user, 'id', None)
        if request.method == 'POST':
            try:
                project_product_id = int(request.data.get('project_product_id'))
            except (TypeError, ValueError) as error:
                raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_PROJECT_PRODUCT_MODULE_TASK_CONFIG_REQUIRED,
                                      error=str(error)) from error
            if not self._has_product_scope(request, project_product_id):
                return ResponseData.fail(RESPONSE_MSG_0210)
            result = ModuleFullTaskConfigService.create_rows(
                project_product_id,
                request.data.get('rows'),
                update_user_id=update_user_id,
            )
            return ResponseData.success(RESPONSE_MSG_0035, result)

        try:
            task_id = int(request.data.get('task_id'))
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID, error=str(error)) from error
        task = Tasks.objects.filter(id=task_id).first()
        if task is None:
            raise TaskCenterError(SYSTEM_TASK_MODULE_CONFIG_MODULE_CONFIG_INVALID)
        if not self._has_task_scope(request, task):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if request.method == 'DELETE':
            ModuleFullTaskConfigService.delete_row(task_id)
            return ResponseData.success(RESPONSE_MSG_0035)
        result = ModuleFullTaskConfigService.update_row(
            task_id,
            request.data.get('row'),
            update_user_id=update_user_id,
        )
        return ResponseData.success(RESPONSE_MSG_0035, result)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def get_id_name(self, request: Request):
        """
        获取定时任务列表
        :param request:
        :return:
        """
        queryset = self.model.objects.select_related('module').all()
        project_product_id = request.query_params.get('project_product_id')
        if project_product_id:
            queryset = queryset.filter(project_product_id=project_product_id)
        module_id = request.query_params.get('module_id')
        if module_id:
            try:
                module_ids = ProductModuleService.module_scope_ids(int(module_id))
            except (TypeError, ValueError):
                module_ids = []
            queryset = queryset.filter(module_id__in=module_ids)
        execution_scope = request.query_params.get('execution_scope')
        if execution_scope:
            queryset = queryset.filter(execution_scope=execution_scope)
        tasks = list(queryset)
        case_type = request.query_params.get('case_type')
        if case_type not in (None, ''):
            try:
                normalized_type = int(case_type)
            except (TypeError, ValueError):
                normalized_type = None
            tasks = [
                task for task in tasks
                if normalized_type is not None
                   and (not task.case_types or normalized_type in task.case_types)
            ]
        data = [
            {
                'key': task.id,
                'title': f'{task.module.name if task.module else "全部模块"}/{task.name}',
                'name': task.name,
                'project_product_id': task.project_product_id,
                'module_id': task.module_id,
                'module_name': task.module.name if task.module else None,
                'case_types': task.case_types,
            }
            for task in tasks
        ]
        return ResponseData.success(RESPONSE_MSG_0099, data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def execution_options(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, ApiConcurrencyService.capacity())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def recent_results(self, request: Request):
        task_ids = []
        for value in str(request.query_params.get('task_ids', '')).split(','):
            try:
                task_id = int(value)
            except (TypeError, ValueError):
                continue
            if task_id > 0 and task_id not in task_ids:
                task_ids.append(task_id)
        task_ids = task_ids[:100]

        tasks = self.model.objects.filter(id__in=task_ids).values('id', 'project_product_id')
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        if user is not None and not (
                PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)
        ):
            allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
            tasks = tasks.filter(project_product_id__in=allowed_ids)
        scoped_task_ids = list(tasks.values_list('id', flat=True))

        return ResponseData.success(
            RESPONSE_MSG_0001,
            TaskRecentResultService.get_recent_results(
                scoped_task_ids,
                request.query_params.get('limit'),
            ),
            headers={
                'Cache-Control': 'no-store, no-cache, max-age=0, must-revalidate',
                'Pragma': 'no-cache',
            },
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def diagnostic_markdown(self, request: Request):
        task = self.model.objects.filter(id=request.query_params.get('id')).first()
        if not task:
            raise TaskCenterError(TASK_SCHEDULE_NOT_FOUND)
        if not self._has_task_scope(request, task):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            DiagnosticMarkdownService.read(
                DiagnosticMarkdownService.TARGET_SCHEDULED_TASK,
                task,
            ),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def trigger_manual(self, request: Request):
        task = Tasks.objects.select_related('project_product', 'case_people').filter(
            id=request.data.get('task_id'),
        ).first()
        if not task:
            raise TaskCenterError(TASK_SCHEDULE_NOT_FOUND)
        if not self._has_task_scope(request, task):
            return ResponseData.fail(RESPONSE_MSG_0210)
        override_provided = 'api_concurrency_limit' in request.data
        api_concurrency_limit = ApiConcurrencyService.resolve_task_trigger_limit(
            task.api_concurrency_limit,
            request.data.get('api_concurrency_limit'),
            override_provided=override_provided,
            error_cls=TaskCenterError,
        )
        temporary_test_envs_provided = request.data.get('test_envs') is not None
        test_envs = (
            ScheduledTaskCaseSelectionService.normalize_test_envs(request.data.get('test_envs'))
            if temporary_test_envs_provided
            else ScheduledTaskCaseSelectionService.task_test_envs(task)
        )
        test_suite_ids = ScheduleDispatchService.create_test_suites(
            task,
            api_concurrency_limit=api_concurrency_limit,
            user_id=request.user.get('id'),
            test_envs=test_envs,
            allow_unconfigured_test_env=temporary_test_envs_provided,
        )
        return ResponseData.success(
            RESPONSE_MSG_0100,
            {
                'test_suite_id': test_suite_ids[0],
                'test_suite_ids': test_suite_ids,
                'test_envs': test_envs,
                'temporary_test_env_override': temporary_test_envs_provided,
                'api_concurrency_limit': api_concurrency_limit,
            },
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def selection_cases(self, request: Request):
        task = Tasks.objects.select_related('project_product', 'module').filter(
            id=request.query_params.get('task_id'),
        ).first()
        if not task:
            raise TaskCenterError(TASK_SCHEDULE_NOT_FOUND)
        if not self._has_task_scope(request, task):
            return ResponseData.fail(RESPONSE_MSG_0210)
        if task.execution_scope == AutomationExecutionScopeEnum.MANUAL.value:
            return ResponseData.fail(RESPONSE_MSG_0282)
        items = ScheduledTaskCaseSelectionService.select_task(task)
        case_id = request.query_params.get('case_id')
        case_name = str(request.query_params.get('case_name') or '').strip().lower()
        module_id = request.query_params.get('module_id')
        raw_case_types = [
            item.strip()
            for value in request.query_params.getlist('case_types')
            for item in str(value).split(',')
            if item.strip()
        ]
        filter_types = ScheduledTaskCaseSelectionService.normalize_case_types(raw_case_types)
        scenario_tags = [
            item
            for value in request.query_params.getlist('scenario_tags')
            for item in str(value).split(',')
            if item
        ]
        allowed_tags = set(ApiCaseScenarioTagEnum.get_key_list())
        scenario_tags = [item for item in scenario_tags if item in allowed_tags]
        if case_id:
            items = [item for item in items if str(item.case_id) == str(case_id)]
        if case_name:
            items = [item for item in items if case_name in item.case_name.lower()]
        if module_id:
            module_ids = ProductModuleService.module_scope_ids(int(module_id))
            items = [item for item in items if item.module_id in module_ids]
        if filter_types:
            items = [item for item in items if item.case_type in filter_types]
        if scenario_tags:
            requested_tags = set(scenario_tags)
            items = [item for item in items if requested_tags.intersection(item.scenario_tags)]
        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(max(int(request.query_params.get('pageSize', 20)), 1), 100)
        count = len(items)
        start = (page - 1) * page_size
        payload = {
            'items': [item.to_dict() for item in items[start:start + page_size]],
            'count': count,
            'page': page,
            'pageSize': page_size,
            'summary': ScheduledTaskCaseSelectionService.summary(
                items,
                execution_scenes=ScheduledTaskCaseSelectionService.task_execution_scenes(task),
            ),
        }
        return ResponseData.success(RESPONSE_MSG_0001, payload, count)


class TasksNoPermissionViews(ViewSet):
    model = Tasks
    serializer_class = TasksSerializers
    authentication_classes = []

    @staticmethod
    def _get_request_user_id(request: Request):
        try:
            auth_result = JwtQueryParamsAuthentication().authenticate(request)
        except Exception:
            return None
        if not auth_result:
            return None
        payload, _ = auth_result
        return payload.get('id')

    @action(methods=['get'], detail=False)
    @error_response('system')
    def trigger_timing(self, request: Request):
        task = Tasks.objects.filter(id=request.query_params.get('id')).first()
        if task is None:
            raise TaskCenterError(TASK_SCHEDULE_NOT_FOUND)
        ScheduleDispatchService.create_test_suites(task)
        return ResponseData.success(RESPONSE_MSG_0100)
