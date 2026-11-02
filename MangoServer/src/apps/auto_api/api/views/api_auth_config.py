# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API授权Token配置

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.api.serializers.api_auth_config import ApiAuthConfigSerializers, ApiAuthConfigSerializersC
from src.apps.auto_api.models import ApiAuthConfig
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.services.api_auth_config import ApiAuthConfigService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0104,
    RESPONSE_MSG_0112,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0210,
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

    @action(methods=['get'], detail=False)
    @error_response('api')
    def targets(self, request: Request):
        product = request.query_params.get('project_product')
        env = request.query_params.get('test_env')
        if not all(str(value).isdigit() for value in (product, env)):
            return ResponseData.fail(RESPONSE_MSG_0003)
        if not ApiAuthConfigCRUD().has_data_scope_permission(request, {'project_product': int(product)}):
            return ResponseData.fail(RESPONSE_MSG_0210)
        return ResponseData.success(RESPONSE_MSG_0001, ApiAuthConfigService.target_options(int(product), int(env)))

    @action(methods=['get'], detail=False)
    @error_response('api')
    def public_variables(self, request: Request):
        product = request.query_params.get('project_product')
        env = request.query_params.get('test_env')
        page = request.query_params.get('page', '1')
        page_size = request.query_params.get('pageSize', '100')
        if not all(str(value).isdigit() for value in (product, env, page, page_size)):
            return ResponseData.fail(RESPONSE_MSG_0003)
        if not ApiAuthConfigCRUD().has_data_scope_permission(request, {'project_product': int(product)}):
            return ResponseData.fail(RESPONSE_MSG_0210)
        queryset = ApiQuerySelector.auth_public_variable_options(int(product), int(env))
        if request.query_params.get('keyword'):
            from django.db.models import Q
            keyword = request.query_params['keyword']
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(key__icontains=keyword))
        total = queryset.count()
        size = min(max(int(page_size), 1), 200)
        start = (max(int(page), 1) - 1) * size
        return ResponseData.success(RESPONSE_MSG_0001, list(queryset.values('id', 'name', 'key', 'type', 'status')[start:start + size]), total)

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
