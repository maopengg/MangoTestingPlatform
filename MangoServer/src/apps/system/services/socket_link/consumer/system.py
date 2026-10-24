# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import json

from django.core.cache import cache
from mangotools.contracts import SocketEnvelopeContract
from mangotools.contracts import TaskPullRequest
from mangotools.enums import CacheValueTypeEnum

from src.apps.auto_pytest.services.test_case.case_flow import PyCaseFlow
from src.apps.auto_ui.services.test_case.case_flow import UiCaseFlow
from src.apps.system.enums import (
    CacheDataKey2Enum,
    ClientTypeEnum,
    SystemConfigManagementLevelEnum,
)
from src.apps.system.services.cache_data import CacheDataService
from src.apps.system.services.system_config import SystemConfigService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.common.decorators.retry import async_task_db_connection


class SystemConsumer:
    @staticmethod
    def _actuator_config_snapshot_key(request_id: str):
        return f'actuator_config_snapshot:{request_id}'

    @staticmethod
    def _actuator_config_save_key(request_id: str):
        return f'actuator_config_save:{request_id}'

    @classmethod
    @async_task_db_connection()
    def t_set_operation_options(cls, data: dict):
        data = {
            'describe': data.get('version'),
            'key': CacheDataKey2Enum.SELECT_VALUE.value,
            'value': json.dumps(data.get('data'), ensure_ascii=False),
            'value_type': CacheValueTypeEnum.DICT.value,
            'group': 'internal',
            'management_level': SystemConfigManagementLevelEnum.INTERNAL.value,
            'is_enabled': True,
        }
        CacheDataService.upsert_unique_key(CacheDataKey2Enum.SELECT_VALUE.value, data)
        SystemConfigService.invalidate(CacheDataKey2Enum.SELECT_VALUE.value)

    @classmethod
    @async_task_db_connection()
    def t_set_userinfo(cls, data):
        from src.apps.system.services.socket_link.connection_service import SocketConnectionService
        from src.apps.system.services.socket_link.message_service import SocketMessageService
        username = data.get('username')
        connection = SocketConnectionService.require_actuator(username)
        SocketConnectionService.update_actuator_runtime(
            connection.user_id,
            is_open=data.get('is_open'),
            debug=data.get('debug'),
            web_live_stream_supported=data.get('web_live_stream_supported'),
        )
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200,
            msg=f'设置用户信息成功，请前往执行器页面查看',
            user=data.get("username"),
            is_notice=ClientTypeEnum.WEB,
        ))

    @classmethod
    @async_task_db_connection()
    def t_set_actuator_config_snapshot(cls, data: dict):
        cls.save_actuator_config_snapshot(data)

    @classmethod
    def save_actuator_config_snapshot(cls, data: dict):
        request_id = data.get('request_id')
        if not request_id:
            return
        cls._sync_socket_user_runtime_status(data)
        cache.set(cls._actuator_config_snapshot_key(request_id), {
            'status': 'success' if data.get('status', True) else 'failed',
            'username': data.get('username'),
            'config': data.get('config') or {},
            'message': data.get('message') or '',
        }, 60)

    @classmethod
    @async_task_db_connection()
    def t_set_actuator_config_save_result(cls, data: dict):
        cls.save_actuator_config_save_result(data)

    @classmethod
    def save_actuator_config_save_result(cls, data: dict):
        request_id = data.get('request_id')
        if not request_id:
            return
        cls._sync_socket_user_runtime_status(data)
        cache.set(cls._actuator_config_save_key(request_id), {
            'status': 'success' if data.get('status', True) else 'failed',
            'username': data.get('username'),
            'message': data.get('message') or '',
            'config': data.get('config') or {},
        }, 60)

    @staticmethod
    def _sync_socket_user_runtime_status(data: dict):
        config = data.get('config') or {}
        runtime_config = config.get('runtime') or {}
        username = data.get('username')
        if not username:
            return
        from src.apps.system.services.socket_link.connection_service import SocketConnectionService
        connection = SocketConnectionService.require_actuator(username)
        if 'is_open' in runtime_config:
            SocketConnectionService.update_actuator_runtime(
                connection.user_id,
                is_open=bool(runtime_config.get('is_open')),
            )
        if 'debug' in runtime_config:
            SocketConnectionService.update_actuator_runtime(
                connection.user_id,
                debug=bool(runtime_config.get('debug')),
            )
        if 'web_live_stream_supported' in runtime_config:
            SocketConnectionService.update_actuator_runtime(
                connection.user_id,
                web_live_stream_supported=bool(runtime_config.get('web_live_stream_supported')),
            )

    @classmethod
    @async_task_db_connection()
    def t_get_task(cls, data: dict):
        data = TaskPullRequest(**data)
        if data.type == TestCaseTypeEnum.UI:
            UiCaseFlow.get_case(data)
        elif data.type == TestCaseTypeEnum.PYTEST:
            PyCaseFlow.get_case(data)
