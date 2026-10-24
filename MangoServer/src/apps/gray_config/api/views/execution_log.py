# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.gray_config.api.serializers.gray_config import GrayExecutionLogSerializerC
from src.apps.gray_config.models import GrayExecutionLog
from src.apps.gray_config.services.execution_log import GrayExecutionLogService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0236, RESPONSE_MSG_0239


class GrayExecutionLogCRUD(ModelCRUD):
    model = GrayExecutionLog
    queryset = GrayExecutionLog.objects.all()
    serializer_class = GrayExecutionLogSerializerC
    serializer = GrayExecutionLogSerializerC
    page_permission_key = 'gray.execution_log'
    not_matching_str = ModelCRUD.not_matching_str + [
        'case_type',
        'config_type',
        'status',
        'action',
        'test_suite_id',
        'case_id',
        'gray_feature',
        'repository',
        'yaml_file',
        'database',
    ]


class GrayExecutionLogViews(ViewSet):
    action_permission_map = {
        'retry_restore': 'gray.execution_log:execute',
        'cleanup_expired': 'gray.execution_log:delete',
    }

    @action(methods=['post'], detail=False)
    @error_response('system')
    def retry_restore(self, request: Request):
        restore_log = GrayExecutionLogService.retry_restore(request.data.get("execution_log_id"))
        return ResponseData.success(
            RESPONSE_MSG_0236,
            {"execution_log_id": restore_log.id, "status": restore_log.status},
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def cleanup_expired(self, request: Request):
        retention_days = int(request.data.get("retention_days") or GrayExecutionLogService.DEFAULT_RETENTION_DAYS)
        deleted = GrayExecutionLogService.cleanup_expired(retention_days)
        return ResponseData.success(
            RESPONSE_MSG_0239,
            {"retention_days": retention_days, "deleted_count": deleted},
        )
