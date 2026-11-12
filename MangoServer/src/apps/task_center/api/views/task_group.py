from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.task_center.exceptions import (
    SYSTEM_TASK_GROUP_TASK_NOT_FOUND,
    SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
    TaskCenterError,
)
from src.apps.task_center.models import ScheduledTaskGroup
from src.apps.task_center.selectors.querysets import ScheduleFireQuerySelector
from src.apps.task_center.services.scheduling.task_group import ScheduledTaskGroupService
from src.apps.task_center.services.scheduling.task_group_execution import ScheduledTaskGroupExecutionService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.exceptions import RESOURCE_ACCESS_DENIED
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0035, RESPONSE_MSG_0100, \
    RESPONSE_MSG_0210, RESPONSE_MSG_0197


class ScheduledTaskGroupTriggerViews(ViewSet):
    model = ScheduledTaskGroup
    http_method_names = ['get', 'options']

    @action(methods=['get'], detail=False)
    @error_response('system')
    def trigger(self, request: Request):
        """触发定时任务组"""
        group_id = ScheduledTaskGroupViews._required_id(request.query_params.get('id'), '任务组ID')
        ScheduledTaskGroupViews._group(request, group_id)
        response = ResponseData.success(
            RESPONSE_MSG_0100,
            ScheduledTaskGroupExecutionService.trigger_manual(group_id),
        )
        response['Cache-Control'] = 'no-store'
        return response


class ScheduledTaskGroupViews(ViewSet):
    model = ScheduledTaskGroup
    page_permission_key = 'timing.tasks'


    @staticmethod
    def _user(request: Request):
        return getattr(getattr(request, 'user', None), 'user_obj', None)

    @staticmethod
    def _required_id(value, label: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
                                  value=(f'{label}格式错误',),
                                  error=str(error),
                                  ) from error

    @classmethod
    def _has_product_scope(cls, request: Request, project_product_id: int) -> bool:
        user = cls._user(request)
        if user is None or PermissionMenuService.is_effective_super_admin(user):
            return True
        return ProjectProductScopeService.has_project_product(user, project_product_id)

    @classmethod
    def _group(cls, request: Request, group_id: int) -> ScheduledTaskGroup:
        group = ScheduledTaskGroup.objects.filter(id=group_id, archived=False).first()
        if group is None:
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_NOT_FOUND)
        if not cls._has_product_scope(request, group.project_product_id):
            raise TaskCenterError(RESOURCE_ACCESS_DENIED)
        return group

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_list(self, request: Request):
        """获取定时任务组列表"""
        query = request.query_params
        filters = {
            'project_product_id': query.get('project_product_id'),
            'module_ids': query.getlist('module_ids') or query.getlist('module_ids[]'),
            'name': query.get('name'),
            'test_envs': query.getlist('test_envs') or query.getlist('test_envs[]'),
            'case_types': query.getlist('case_types') or query.getlist('case_types[]'),
            'execution_scenes': (
                    query.getlist('execution_scenes') or query.getlist('execution_scenes[]')
            ),
            'status': query.get('status'),
            'is_notice': query.get('is_notice'),
            'sync_status': query.get('sync_status'),
            'page': query.get('page'),
            'pageSize': query.get('pageSize'),
        }
        user = self._user(request)
        if (
                user is not None
                and not PermissionMenuService.is_effective_super_admin(user)
                and not ProjectProductScopeService.can_view_all_project_data(user)
        ):
            allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
            requested = filters['project_product_id']
            if requested not in (None, '') and int(requested) not in allowed_ids:
                return ResponseData.fail(RESPONSE_MSG_0210)
            if requested in (None, ''):
                filters['project_product_ids'] = allowed_ids
        return ResponseData.success(RESPONSE_MSG_0001, ScheduledTaskGroupService.list(filters))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_options(self, request: Request):
        """获取定时任务组选项"""
        requested = request.query_params.get('project_product_id')
        user = self._user(request)
        if requested not in (None, ''):
            project_product_id = self._required_id(requested, '项目产品ID')
            if not self._has_product_scope(request, project_product_id):
                return ResponseData.fail(RESPONSE_MSG_0210)
            project_product_ids = [project_product_id]
        elif (
                user is not None
                and not PermissionMenuService.is_effective_super_admin(user)
                and not ProjectProductScopeService.can_view_all_project_data(user)
        ):
            project_product_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        else:
            project_product_ids = None
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ScheduledTaskGroupService.options(project_product_ids),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_detail(self, request: Request):
        """获取定时任务组详情"""
        group_id = self._required_id(request.query_params.get('id'), '任务组ID')
        self._group(request, group_id)
        return ResponseData.success(RESPONSE_MSG_0001, ScheduledTaskGroupService.detail(group_id))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def latest_executions(self, request: Request):
        """获取定时任务组最近执行批次"""
        group_id = self._required_id(request.query_params.get('id'), '任务组ID')
        self._group(request, group_id)
        return ResponseData.success(RESPONSE_MSG_0001, ScheduleFireQuerySelector.latest_group_executions(group_id))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def resend_notice(self, request: Request):
        """重发定时任务组执行通知"""
        group_id = self._required_id(request.data.get('id'), '任务组ID')
        self._group(request, group_id)
        execution_id = self._required_id(request.data.get('execution_id'), '执行批次ID')
        ScheduledTaskGroupExecutionService.resend_notice(group_id, execution_id)
        return ResponseData.success(RESPONSE_MSG_0197)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def preview(self, request: Request):
        """预览定时任务组"""
        product_id = self._required_id(request.data.get('project_product_id'), '项目产品ID')
        if not self._has_product_scope(request, product_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        group_id = request.data.get('id')
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ScheduledTaskGroupService.preview(
                request.data,
                group_id=self._required_id(group_id, '任务组ID') if group_id not in (None, '') else None,
            ),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def create(self, request: Request):
        """创建定时任务组"""
        product_id = self._required_id(request.data.get('project_product_id'), '项目产品ID')
        if not self._has_product_scope(request, product_id):
            return ResponseData.fail(RESPONSE_MSG_0210)
        user = self._user(request)
        result = ScheduledTaskGroupService.create(
            request.data,
            update_user_id=getattr(user, 'id', None),
        )
        return ResponseData.success(RESPONSE_MSG_0035, result)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def update(self, request: Request):
        """更新定时任务组"""
        group_id = self._required_id(request.data.get('id'), '任务组ID')
        self._group(request, group_id)
        user = self._user(request)
        result = ScheduledTaskGroupService.update(
            group_id,
            request.data,
            update_user_id=getattr(user, 'id', None),
        )
        return ResponseData.success(RESPONSE_MSG_0035, result)

    @action(methods=['delete'], detail=False)
    @error_response('system')
    def delete(self, request: Request):
        """删除定时任务组"""
        group_id = self._required_id(request.data.get('id'), '任务组ID')
        self._group(request, group_id)
        ScheduledTaskGroupService.delete(group_id)
        return ResponseData.success(RESPONSE_MSG_0035)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def set_member_status(self, request: Request):
        """设置定时任务组成员启用状态"""
        group_id = self._required_id(request.data.get('group_id'), '任务组ID')
        self._group(request, group_id)
        enabled = request.data.get('enabled')
        if enabled not in (True, False, 0, 1):
            raise TaskCenterError(SYSTEM_TASK_GROUP_TASK_CONFIG_INVALID,
                                  value=('子任务启用状态只能是布尔值',),
                                  )
        user = self._user(request)
        result = ScheduledTaskGroupService.set_member_enabled(
            group_id,
            self._required_id(request.data.get('member_id'), '任务组成员ID'),
            bool(enabled),
            update_user_id=getattr(user, 'id', None),
        )
        return ResponseData.success(RESPONSE_MSG_0035, result)
