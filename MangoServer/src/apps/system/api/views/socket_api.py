# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-05-13 23:00
# @Author : 毛鹏

import uuid
from urllib.parse import urlparse

from django.core.cache import cache
from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract, UiRecordingCommand
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.enums import ServerUiCommandEnum, ServerToolsCommandEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.models import TestObject, ProjectProduct
from src.apps.user.models import User
from src.apps.user.services.user_cache import UserCacheService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import get_request_project_id, get_request_project_product_id
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0059,
    RESPONSE_MSG_0101,
    RESPONSE_MSG_0102,
    RESPONSE_MSG_0113,
    RESPONSE_MSG_0121,
    RESPONSE_MSG_0139,
)


class SocketApiViews(ViewSet):
    action_permission_map = {
        'get_user_list': 'equipment.actuator:detail',
        'get_current_actuator_status': 'ui.case:execute',
        'get_all_user_sum': 'equipment.actuator:detail',
        'get_all_user_list': 'equipment.actuator:detail',
        'set_user_open_status': 'equipment.actuator:status',
        'set_user_debug': 'equipment.actuator:debug',
        'request_actuator_config': 'equipment.actuator:detail',
        'get_actuator_config_result': 'equipment.actuator:detail',
        'update_actuator_config': 'equipment.actuator:edit',
        'get_actuator_config_save_result': 'equipment.actuator:detail',
        'get_new_browser_obj': 'ui.page:debug',
    }

    ACTUATOR_CONFIG_CACHE_TTL = 60

    @staticmethod
    def _actuator_config_snapshot_key(request_id: str):
        return f'actuator_config_snapshot:{request_id}'

    @staticmethod
    def _actuator_config_save_key(request_id: str):
        return f'actuator_config_save:{request_id}'

    @staticmethod
    def _actuator_payload(connection, is_owner: bool = False):
        from src.apps.auto_ui.services.executor_slot import ExecutorSlotLeaseService

        return {
            'id': connection.user.id,
            'name': connection.user.name,
            'username': connection.user.username,
            'ip': connection.user.ip,
            'is_open': connection.is_open,
            'debug': connection.debug,
            'web_live_stream_supported': connection.web_live_stream_supported,
            'connection_id': str(connection.connection_id),
            'last_seen_at': connection.last_seen_at,
            'is_owner': is_owner,
            **ExecutorSlotLeaseService.occupancy(connection),
        }

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_user_list(self, request: Request):
        data = [
            self._actuator_payload(connection, connection.user_id == request.user['id'])
            for connection in SocketConnectionService.list_online_actuators()
        ]
        return ResponseData.success(RESPONSE_MSG_0101, data, len(data))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_current_actuator_status(self, request: Request):
        user_id = request.user.get('id') if isinstance(request.user, dict) else None
        connection = SocketConnectionService.get_current_actuator(user_id) if user_id else None
        is_online = connection is not None and SocketConnectionService.is_actuator_online(user_id)
        available_actuators = [
            self._actuator_payload(item, item.user_id == user_id)
            for item in SocketConnectionService.list_online_actuators()
            if item.user_id == user_id or item.is_open
        ]
        return ResponseData.success(RESPONSE_MSG_0101, {
            'online': is_online,
            'actuator': self._actuator_payload(connection, True) if is_online else None,
            'available_actuators': available_actuators,
            'is_open': bool(connection.is_open) if connection else False,
            'debug': bool(connection.debug) if connection else False,
            'last_seen_at': connection.last_seen_at if connection else None,
        })

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_all_user_sum(self, request: Request):
        data = len(SocketConnectionService.list_online_actuators())
        return ResponseData.success(RESPONSE_MSG_0102, {'sum': data})

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_all_user_list(self, request: Request):
        data = [
            {
                'user_id': connection.user_id,
                'username': connection.user.username,
                'connection_id': str(connection.connection_id),
                'client_type': connection.client_type,
                'service_instance': connection.service_instance,
                'last_seen_at': connection.last_seen_at,
            }
            for connection in SocketConnectionService.list_online_actuators()
        ]
        return ResponseData.success(RESPONSE_MSG_0102, data, )

    @action(methods=['put'], detail=False)
    @error_response('system')
    def set_user_open_status(self, request: Request):
        status = request.data.get('status')
        username = request.data.get('username')
        connection = SocketConnectionService.require_actuator(username)
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg=f'更新执行器OPEN状态：{bool(status)}',
            user=username,
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=ServerUiCommandEnum.SET_OPEN_STATUS.value,
                func_args={'is_open': bool(status)}),
        ))
        connection = SocketConnectionService.update_actuator_runtime(connection.user_id, is_open=bool(status))
        return ResponseData.success(RESPONSE_MSG_0113, {
            'user_id': connection.user_id,
            'username': username,
            'is_open': connection.is_open
        })

    @action(methods=['put'], detail=False)
    @error_response('system')
    def set_user_debug(self, request: Request):
        status = request.data.get('status')
        username = request.data.get('username')
        connection = SocketConnectionService.require_actuator(username)
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg=f'更新执行器DEBUG状态：{bool(status)}',
            user=username,
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=ServerUiCommandEnum.SET_DEBUG.value,
                func_args={'debug': bool(status)}),
        ))
        connection = SocketConnectionService.update_actuator_runtime(connection.user_id, debug=bool(status))
        return ResponseData.success(RESPONSE_MSG_0139, {
            'user_id': connection.user_id,
            'username': username,
            'debug': connection.debug
        })

    @action(methods=['post'], detail=False)
    @error_response('system')
    def request_actuator_config(self, request: Request):
        username = (request.data.get('username') or '').strip()
        SocketConnectionService.require_actuator(username)
        request_id = str(uuid.uuid4())
        cache.set(self._actuator_config_snapshot_key(request_id), {
            'status': 'pending',
            'username': username,
        }, self.ACTUATOR_CONFIG_CACHE_TTL)
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg='读取执行器配置',
            user=username,
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=ServerToolsCommandEnum.GET_ACTUATOR_CONFIG.value,
                func_args={'request_id': request_id}),
        ))
        return ResponseData.success(RESPONSE_MSG_0101, {'request_id': request_id})

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_actuator_config_result(self, request: Request):
        request_id = request.query_params.get('request_id')
        data = cache.get(self._actuator_config_snapshot_key(request_id))
        if not data:
            return ResponseData.success(RESPONSE_MSG_0101, {'status': 'expired'})
        return ResponseData.success(RESPONSE_MSG_0101, data)

    @action(methods=['put'], detail=False)
    @error_response('system')
    def update_actuator_config(self, request: Request):
        username = (request.data.get('username') or '').strip()
        config = request.data.get('config') or {}
        SocketConnectionService.require_actuator(username)
        request_id = str(uuid.uuid4())
        cache.set(self._actuator_config_save_key(request_id), {
            'status': 'pending',
            'username': username,
        }, self.ACTUATOR_CONFIG_CACHE_TTL)
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg='保存执行器配置',
            user=username,
            is_notice=ClientTypeEnum.ACTUATOR,
            data=SocketCommandContract(
                func_name=ServerToolsCommandEnum.UPDATE_ACTUATOR_CONFIG.value,
                func_args={'request_id': request_id, 'config': config}),
        ))
        return ResponseData.success(RESPONSE_MSG_0113, {'request_id': request_id})

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_actuator_config_save_result(self, request: Request):
        request_id = request.query_params.get('request_id')
        data = cache.get(self._actuator_config_save_key(request_id))
        if not data:
            return ResponseData.success(RESPONSE_MSG_0101, {'status': 'expired'})
        return ResponseData.success(RESPONSE_MSG_0101, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_new_browser_obj(self, request: Request):
        """
        @param request:
        @return:
        """
        is_recording = request.query_params.get('is_recording')
        if is_recording == '1':
            user_obj = User.objects.get(id=request.user['id'])
            selected_environment = UserCacheService.selected_environment(user_obj)
            project_id = get_request_project_id(request)
            project_product_id = get_request_project_product_id(request)
            project_product_queryset = ProjectProduct.objects.all()
            if project_product_id:
                project_product_queryset = project_product_queryset.filter(id=project_product_id)
            elif project_id:
                project_product_queryset = project_product_queryset.filter(project_id=project_id)
            host_list: list[dict] = list(TestObject.objects
                                         .filter(
                project_product_id__in=project_product_queryset.values_list('id', flat=True),
                environment=selected_environment,
                auto_type__in=[AutoTypeEnum.API.value, AutoTypeEnum.CURRENCY.value])
                                         .values('value', 'project_product_id'))
            if not host_list:
                return ResponseData.fail(RESPONSE_MSG_0121, )
            host_list_dict = []
            for i in host_list:
                host_list_dict.append({
                    'value': urlparse(i.get('value')).netloc,
                    'project_product_id': i.get('project_product_id')
                })
            send_socket_data = SocketEnvelopeContract(
                code=200,
                msg="实例化web对象",
                user=request.user.get('username'),
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(
                    func_name=ServerUiCommandEnum.RECORDING.value,
                    func_args=UiRecordingCommand(url_list=host_list)
                )
            )
        else:
            send_socket_data = SocketEnvelopeContract(
                code=200,
                msg="实例化web对象",
                user=request.user.get('username'),
                is_notice=ClientTypeEnum.ACTUATOR,
                data=SocketCommandContract(
                    func_name=ServerUiCommandEnum.NEW_PAGE_OBJ.value,
                    func_args={}
                )
            )
        SocketConnectionService.require_actuator(send_socket_data.user)
        SocketMessageService.send_socket_data(send_socket_data)
        return ResponseData.success(RESPONSE_MSG_0059, )
