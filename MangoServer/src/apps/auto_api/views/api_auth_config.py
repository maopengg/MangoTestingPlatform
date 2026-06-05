# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API授权Token配置

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiAuthConfig
from src.apps.auto_api.service.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.views.api_info import ApiInfoSerializersC
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_system.views.time_tasks import TimeTasksSerializers
from src.common.enums.api_enum import ApiAuthRefreshModeEnum, ApiAuthTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class ApiAuthConfigSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    expires_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)
    last_refresh_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)

    class Meta:
        model = ApiAuthConfig
        fields = '__all__'

    def validate(self, attrs):
        auth_type = attrs.get('auth_type', getattr(self.instance, 'auth_type', None))
        api_info = attrs.get('api_info', getattr(self.instance, 'api_info', None))
        custom_code = attrs.get('custom_code', getattr(self.instance, 'custom_code', None))
        refresh_mode = attrs.get('refresh_mode', getattr(self.instance, 'refresh_mode', None))
        time_task = attrs.get('time_task', getattr(self.instance, 'time_task', None))
        token_ttl = attrs.get('token_ttl', getattr(self.instance, 'token_ttl', 1440))
        refresh_margin = attrs.get('refresh_margin', getattr(self.instance, 'refresh_margin', 5))
        project_product = attrs.get('project_product', getattr(self.instance, 'project_product', None))

        if auth_type == ApiAuthTypeEnum.API.value and not api_info:
            raise serializers.ValidationError({'api_info': '接口登录授权必须选择登录接口'})
        if auth_type == ApiAuthTypeEnum.API.value and api_info and project_product and api_info.project_product_id != project_product.id:
            raise serializers.ValidationError({'api_info': '登录接口必须属于当前项目产品'})
        if auth_type == ApiAuthTypeEnum.CUSTOM.value and not custom_code:
            raise serializers.ValidationError({'custom_code': '自定义代码授权必须填写代码'})
        if refresh_mode in [ApiAuthRefreshModeEnum.TIMING.value, ApiAuthRefreshModeEnum.BOTH.value] and not time_task:
            raise serializers.ValidationError({'time_task': '定时刷新必须选择定时策略'})
        if refresh_mode in [ApiAuthRefreshModeEnum.PASSIVE.value, ApiAuthRefreshModeEnum.BOTH.value]:
            if token_ttl <= 0:
                raise serializers.ValidationError({'token_ttl': 'Token有效期必须大于0'})
            if refresh_margin < 0:
                raise serializers.ValidationError({'refresh_margin': '提前刷新时间不能小于0'})
            if refresh_margin >= token_ttl:
                raise serializers.ValidationError({'refresh_margin': '提前刷新时间必须小于Token有效期'})
        attrs['cache_keys'] = []
        return attrs


class ApiAuthConfigSerializersC(ApiAuthConfigSerializers):
    project_product = ProjectProductSerializersC(read_only=True)
    api_info = ApiInfoSerializersC(read_only=True)
    time_task = TimeTasksSerializers(read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('project_product', 'api_info', 'time_task')


class ApiAuthConfigCRUD(ModelCRUD):
    model = ApiAuthConfig
    queryset = ApiAuthConfig.objects.all()
    serializer_class = ApiAuthConfigSerializersC
    serializer = ApiAuthConfigSerializers
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'auth_type',
        'refresh_mode',
        'last_refresh_status',
        'time_task',
        'api_info',
    ]


class ApiAuthConfigViews(ViewSet):
    model = ApiAuthConfig
    serializer_class = ApiAuthConfigSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_status(self, request: Request):
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
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
