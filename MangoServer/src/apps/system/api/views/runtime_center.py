from pydantic import ValidationError
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.exceptions import (
    SYSTEM_FRONTEND_PARAMETER_INVALID,
    SystemError,
)
from src.apps.system.schemas.error import FrontendErrorReport
from src.apps.system.services.runtime_center.diagnostics import DiagnosticsService
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.overview import RuntimeOverviewService
from src.apps.system.services.runtime_center.queue_stats import QueueStatsService
from src.apps.system.services.runtime_center.recent_errors import RecentErrorsService
from src.apps.system.services.runtime_center.system_error_event import (
    SystemErrorEventService,
    SystemErrorEventSource,
)
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0320


class RuntimeCenterViews(ViewSet):
    action_permission_map = {
        'overview': 'system.runtime_center',
        'services': 'system.runtime_center:detail',
        'queues': 'system.runtime_center:detail',
        'diagnostics': 'system.runtime_center:detail',
        'recent_errors': 'system.error_record',
        # 所有已登录 Web 用户都可能产生前端运行异常，不能绑定系统运维菜单权限。
        'report_frontend_error': 'index.home',
    }

    @action(methods=['get'], detail=False)
    @error_response('system')
    def overview(self, request: Request):
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        return ResponseData.success(RESPONSE_MSG_0001, RuntimeOverviewService.visible_overview(user))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def services(self, request: Request):
        RuntimeOverviewService.report_core_api()
        return ResponseData.success(
            RESPONSE_MSG_0001,
            ServiceHeartbeatService.list_service_groups(RuntimeOverviewService.SERVICE_NAMES),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def queues(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, QueueStatsService.get_stats())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def diagnostics(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, DiagnosticsService.list_diagnostics())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def recent_errors(self, request: Request):
        page = max(int(request.query_params.get('page') or 1), 1)
        page_size = min(max(int(request.query_params.get('pageSize') or RecentErrorsService.DEFAULT_LIMIT), 1), 100)
        rows, total = RecentErrorsService.paginate_errors(
            page,
            page_size,
            category=request.query_params.get('category'),
            keyword=request.query_params.get('keyword'),
            source=request.query_params.get('source'),
        )
        user = getattr(getattr(request, 'user', None), 'user_obj', None)
        return ResponseData.success(RESPONSE_MSG_0001, RecentErrorsService.visible_rows(rows, user), total_size=total)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def report_frontend_error(self, request: Request):
        try:
            model = FrontendErrorReport.model_validate(request.data or {})
        except ValidationError as error:
            raise SystemError(SYSTEM_FRONTEND_PARAMETER_INVALID, error=str(error)) from error
        username = request.user.get('username') if isinstance(request.user, dict) else None
        SystemErrorEventService.record(
            service_name=f'web-console:{username or "unknown"}'[:64],
            source=SystemErrorEventSource.FRONTEND,
            request_path=model.operation,
            exception_type=model.exception_type,
            message=model.message,
            trace=model.traceback,
        )
        return ResponseData.success(RESPONSE_MSG_0320)
