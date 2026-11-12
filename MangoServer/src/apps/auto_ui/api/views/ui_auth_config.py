from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract
from pydantic import ValidationError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_ui.api.serializers.ui_auth_config import UiAuthConfigSerializers, UiAuthConfigSerializersC
from src.apps.auto_ui.exceptions import UI_AUTH_CACHE_STRUCTURE_INVALID
from src.apps.auto_ui.models import UiAuthConfig
from src.apps.auto_ui.schemas.auth import UiAuthCache
from src.apps.auto_ui.services.authentication.ui_auth import UiAuthManager
from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import ExecutorModeEnum
from src.apps.system.enums import ServerUiCommandEnum
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0059,
    RESPONSE_MSG_0104,
    RESPONSE_MSG_0112,
    RESPONSE_MSG_0247,
)


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: UI授权配置


class UiAuthConfigCRUD(ModelCRUD):
    model = UiAuthConfig
    queryset = UiAuthConfig.objects.all()
    serializer_class = UiAuthConfigSerializersC
    serializer = UiAuthConfigSerializers
    page_permission_key = 'ui.auth_config'
    not_matching_str = ModelCRUD.not_matching_str + [
        'test_env',
        'auth_type',
        'refresh_mode',
        'last_refresh_status',
        'page_step',
        'time_task',
        'notice_group',
    ]


class UiAuthConfigViews(ViewSet):
    model = UiAuthConfig
    serializer_class = UiAuthConfigSerializers

    @action(methods=['put'], detail=False)
    @error_response('ui')
    def put_status(self, request: Request):
        """设置UI 授权配置启用状态"""
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        obj.save(update_fields=["status", "update_user", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0104)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def refresh(self, request: Request):
        """刷新UI 授权配置的授权结果"""
        data = UiAuthManager.refresh(request.data.get('id'))
        return ResponseData.success(RESPONSE_MSG_0112, data=data)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def clear(self, request: Request):
        """清除UI 授权配置的授权缓存"""
        data = UiAuthManager.clear(request.data.get('id'))
        return ResponseData.success(RESPONSE_MSG_0104, data=data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def cache(self, request: Request):
        """查看UI 授权配置的授权缓存"""
        data = UiAuthManager.preview(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0001, data=data)

    @action(methods=['put', 'post'], detail=False)
    @error_response('ui')
    def manual_cache(self, request: Request):
        """手动保存 UI 授权缓存"""
        cache_data = request.data.get('manual_config')
        if cache_data is None:
            cache_data = request.data.get('cache_data') or {}
        try:
            cache_data = UiAuthCache.model_validate(cache_data).model_dump(mode='json')
        except ValidationError as error:
            raise serializers.ValidationError(
                {'manual_config': UI_AUTH_CACHE_STRUCTURE_INVALID.message.format(error)}) from error
        data = UiAuthManager.save_manual_auth_cache(request.data.get('id'), cache_data)
        return ResponseData.success(RESPONSE_MSG_0104, data=data)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def auto_start(self, request: Request):
        """启动 UI 自动授权流程"""
        config = self.model.objects.get(id=request.data.get('id'))
        auto_config = config.auto_auth_config or {}
        test_object_url = UiAuthManager.resolve_test_object_url(config)
        origin = UiAuthManager.resolve_origin(config)
        task = SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg='开始UI自动授权',
            user=request.user.get('username'),
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=ServerUiCommandEnum.AUTH_AUTO.value,
                func_args={
                    'config_id': config.id,
                    'url': auto_config.get('url') or test_object_url,
                    'origin': origin,
                    'cookie_domains': auto_config.get('cookie_domains') or [],
                    'local_storage_keys': auto_config.get('local_storage_keys') or [],
                    'session_storage_keys': auto_config.get('session_storage_keys') or [],
                    'headers': auto_config.get('headers') or {},
                    'timeout': auto_config.get('timeout') or 300,
                    'send_user': request.user.get('username'),
                }
            )
        ), executor_mode=ExecutorModeEnum.SELF.value, ttl_seconds=0)
        return ResponseData.success(RESPONSE_MSG_0059, {
            'task_id': task.id,
            'task_status': task.status,
        })

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def auto_capture(self, request: Request):
        """采集 UI 自动授权结果"""
        config = self.model.objects.get(id=request.data.get('id'))
        auto_config = config.auto_auth_config or {}
        origin = UiAuthManager.resolve_origin(config)
        task = SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg='提取UI自动授权缓存',
            user=request.user.get('username'),
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=ServerUiCommandEnum.AUTH_AUTO_CAPTURE.value,
                func_args={
                    'config_id': config.id,
                    'origin': origin,
                    'cookie_domains': auto_config.get('cookie_domains') or [],
                    'local_storage_keys': auto_config.get('local_storage_keys') or [],
                    'session_storage_keys': auto_config.get('session_storage_keys') or [],
                    'headers': auto_config.get('headers') or {},
                    'send_user': request.user.get('username'),
                }
            )
        ), executor_mode=ExecutorModeEnum.SELF.value, ttl_seconds=0)
        return ResponseData.success(RESPONSE_MSG_0247, {
            'task_id': task.id,
            'task_status': task.status,
        })
