# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API授权Token配置

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_auth_config import ApiAuthConfigSerializers, ApiAuthConfigSerializersC
from src.apps.auto_api.models import ApiAuthConfig
from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0104,
    RESPONSE_MSG_0112,
)
from src.common.responses.update_audit import ApiUpdateUserCRUDMixin, save_update_user


class ApiAuthConfigCRUD(ApiUpdateUserCRUDMixin, ModelCRUD):
    model = ApiAuthConfig
    queryset = ApiAuthConfig.objects.all()
    serializer_class = ApiAuthConfigSerializersC
    serializer = ApiAuthConfigSerializers
    page_permission_key = 'api.auth_config'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'auth_type',
        'refresh_mode',
        'last_refresh_status',
        'time_task',
        'notice_group',
        'api_info',
        'update_user',
    ]


class ApiAuthConfigViews(ViewSet):
    model = ApiAuthConfig
    serializer_class = ApiAuthConfigSerializers
    action_permission_map = {
        'put_status': 'api.auth_config:status',
        'refresh': 'api.auth_config:debug',
        'clear': 'api.auth_config:debug',
        'cache': 'api.auth_config:detail',
    }

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_status(self, request: Request):
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        save_update_user(obj, request, ['status'])
        return ResponseData.success(RESPONSE_MSG_0104)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def refresh(self, request: Request):
        data = ApiAuthManager.refresh(request.data.get('id'), force=True, raise_error=True)
        return ResponseData.success(RESPONSE_MSG_0112, data=data)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def clear(self, request: Request):
        data = ApiAuthManager.clear(request.data.get('id'))
        return ResponseData.success(RESPONSE_MSG_0104, data=data)

    @action(methods=['get'], detail=False)
    @error_response('api')
    def cache(self, request: Request):
        data = ApiAuthManager.preview(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0001, data=data)
