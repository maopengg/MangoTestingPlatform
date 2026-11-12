from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.common.decorators.error_response import error_response
from src.common.responses import RESPONSE_MSG_0001, RESPONSE_MSG_0161, RESPONSE_MSG_0162
from src.common.responses.response_data import ResponseData


class SystemJobViews(ViewSet):

    @action(methods=['get'], detail=False)
    @error_response('system')
    def list(self, request: Request):
        """获取系统定时任务列表"""
        try:
            page = max(1, int(request.query_params.get('page') or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(100, max(1, int(request.query_params.get('pageSize') or 20)))
        except (TypeError, ValueError):
            page_size = 20
        filters = {
            key: str(request.query_params.get(key) or '').strip()
            for key in (
                'key', 'name', 'description', 'cron', 'latest_error_message',
                'source_type__in', 'latest_status__in',
            )
        }
        jobs, total = SystemJobService.list_jobs(page=page, page_size=page_size, filters=filters)
        return ResponseData.success(RESPONSE_MSG_0001, jobs, total)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def trigger(self, request: Request):
        """触发系统定时任务"""
        job_key = request.data.get('job_key')
        fire = SystemJobService.trigger(job_key)
        if not fire:
            return ResponseData.fail(RESPONSE_MSG_0162)
        return ResponseData.success(RESPONSE_MSG_0161, {'fire_id': fire.id, 'status': fire.status})
