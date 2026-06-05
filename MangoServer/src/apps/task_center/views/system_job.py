from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.task_center.services.system_job_service import SystemJobService
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view import RESPONSE_MSG_0001, RESPONSE_MSG_0161, RESPONSE_MSG_0162
from src.common.tools.view.response_data import ResponseData


class SystemJobViews(ViewSet):
    @action(methods=['get'], detail=False)
    @error_response('system')
    def list(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, SystemJobService.list_jobs(), len(SystemJobService.JOBS))

    @action(methods=['post'], detail=False)
    @error_response('system')
    def trigger(self, request: Request):
        job_key = request.data.get('job_key')
        fire = SystemJobService.trigger(job_key)
        if not fire:
            return ResponseData.fail(RESPONSE_MSG_0162)
        return ResponseData.success(RESPONSE_MSG_0161, {'fire_id': fire.id, 'status': fire.status})
