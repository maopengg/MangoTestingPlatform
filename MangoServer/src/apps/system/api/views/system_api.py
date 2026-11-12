# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import json
import re

from django.conf import settings
from mangotools.enums import CacheValueTypeEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.enums import (
    CacheDataKey2Enum,
    ClientTypeEnum,
    ServerToolsCommandEnum,
    SystemConfigManagementLevelEnum,
)
from src.apps.system.services.catalog.assertion_catalog import AssertionCatalogService
from src.apps.system.services.catalog.enum_catalog import EnumCatalogService
from src.apps.system.services.configuration.logging_level import LoggingLevelService
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.common.decorators.error_response import error_response
from src.common.exceptions import MangoServerError
from src.common.responses import ResponseData
from src.common.responses.response_msg import ASSERTION_METHOD_REQUIRED
from src.common.responses.response_msg import (
    RESPONSE_MSG_0060,
    RESPONSE_MSG_0061,
    RESPONSE_MSG_0062,
    RESPONSE_MSG_0063,
    RESPONSE_MSG_0076,
    RESPONSE_MSG_0136,
    RESPONSE_MSG_0201,
    RESPONSE_MSG_0202,
)
from src.common.testing import ObtainAssertion, ObtainTestData, assertion_func_info, get_data_method_info


class SystemViews(ViewSet):

    METHOD_CACHE_TYPES = {
        'test_data': CacheDataKey2Enum.TEST_DATA_SELECT_VALUE.value,
        'api_assertion': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
        'ui_operation': CacheDataKey2Enum.SELECT_VALUE.value,
    }

    @staticmethod
    def _find_assertion_method(method_name: str):
        for type_group in assertion_func_info:
            for class_group in type_group.get('children') or []:
                for method in class_group.get('children') or []:
                    if method.get('value') == method_name:
                        return method
        return None

    @classmethod
    def _execute_assertion_test_groups(cls, groups: list) -> dict:
        assertion = ObtainAssertion(test_data=ObtainTestData())
        group_results = []
        for group_index, group in enumerate(groups, start=1):
            group = group if isinstance(group, dict) else {}
            group_name = str(group.get('name') or f'断言组{group_index}')
            group_logic = str(group.get('logic') or 'AND').upper()
            if group_logic not in {'AND', 'OR'}:
                group_logic = 'AND'
            items = group.get('items') if isinstance(group.get('items'), list) else []
            item_results = []
            for item in items:
                item = item if isinstance(item, dict) else {}
                method = str(item.get('method') or '').strip()
                method_info = cls._find_assertion_method(method) if method else None
                if not method_info:
                    item_results.append({
                        'method': method,
                        'label': method or '未选择断言方法',
                        'status': False,
                        'message': '断言方法不存在或未选择',
                        'actual': item.get('actual'),
                        'expect': item.get('expect'),
                    })
                    continue
                try:
                    message = assertion.ass(
                        method=method,
                        actual=item.get('actual'),
                        expect=item.get('expect'),
                    )
                    status = True
                    message = message or '断言通过'
                except Exception as error:
                    status = False
                    message = str(error)
                item_results.append({
                    'method': method,
                    'label': method_info.get('label') or method,
                    'status': status,
                    'message': message,
                    'actual': item.get('actual'),
                    'expect': item.get('expect'),
                })
            statuses = [item.get('status') is True for item in item_results]
            group_status = (
                all(statuses) if group_logic == 'AND' else any(statuses)
            ) if statuses else False
            group_results.append({
                'name': group_name,
                'logic': group_logic,
                'status': group_status,
                'items': item_results,
            })
        overall_status = bool(group_results) and all(group.get('status') for group in group_results)
        passed_count = sum(1 for group in group_results if group.get('status'))
        return {
            'status': overall_status,
            'message': (
                f'全部断言组通过，共{len(group_results)}组'
                if overall_status
                else f'断言组未全部通过：{passed_count}/{len(group_results)}组通过'
            ),
            'groups': group_results,
        }

    @staticmethod
    def _upsert_method_cache(key: str, value, describe: str):
        from src.apps.system.services.configuration.cache_data import CacheDataService
        from src.apps.system.services.configuration.system_config import SystemConfigService

        data = {
            'describe': describe,
            'key': key,
            'value': json.dumps(value, ensure_ascii=False),
            'value_type': CacheValueTypeEnum.DICT.value,
            'group': 'internal',
            'management_level': SystemConfigManagementLevelEnum.INTERNAL.value,
            'is_enabled': True,
        }
        CacheDataService.upsert_unique_key(key, data)
        SystemConfigService.invalidate(key)

    @staticmethod
    def _get_cache_value(key: str):
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get(key)

    @staticmethod
    def _get_method_cache_value(key: str):
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get(key, default={})

    @staticmethod
    def _get_request_username(request: Request):
        if isinstance(request.user, dict):
            return request.user.get('username')
        return getattr(request.user, 'username', None)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def enum_api(self, request: Request):
        """获取系统显式注册的枚举选项"""
        return ResponseData.success(
            RESPONSE_MSG_0076,
            EnumCatalogService.catalog(),
        )

    @action(methods=['get'], detail=False)
    @error_response('system')
    def common_variable(self, request: Request):
        """
        返回公共变量页
        @param request:
        @return:
        """
        return ResponseData.success(RESPONSE_MSG_0061, get_data_method_info())

    @action(methods=['get'], detail=False)
    @error_response('system')
    def random_data(self, request: Request):
        """执行测试数据生成方法并返回结果"""
        name = (request.GET.get("name") or "").strip()
        if name.startswith("${{") and name.endswith("}}"):
            name = name[3:-2].strip()
        elif name.startswith("${") and name.endswith("}"):
            name = name[2:-1].strip()
        if not name:
            return ResponseData.fail(RESPONSE_MSG_0063)
        match = re.search(r'\((.*?)\)', name)
        if match:
            try:
                return ResponseData.success(RESPONSE_MSG_0062, str(ObtainTestData().regular(name)))
            except MangoServerError as error:
                return ResponseData.fail((error.code, error.msg), )
        return ResponseData.fail(RESPONSE_MSG_0060)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def assertion_list(self, request: Request):
        """
        返回断言方法页
        @param request:
        @return:
        """
        return ResponseData.success(
            (200, '获取断言方法成功'),
            AssertionCatalogService.catalog(),
        )

    @action(methods=['post'], detail=False)
    @error_response('system')
    def method_cache_refresh(self, request: Request):
        """刷新测试数据、断言或 UI 操作方法目录"""
        cache_type = (request.data.get('type') or '').strip()
        if cache_type == 'all':
            types = ['test_data', 'api_assertion', 'ui_operation']
        elif cache_type in self.METHOD_CACHE_TYPES:
            types = [cache_type]
        else:
            return ResponseData.fail(RESPONSE_MSG_0202)

        result = {}
        for item_type in types:
            cache_key = self.METHOD_CACHE_TYPES[item_type]
            if item_type == 'test_data':
                ObtainTestData()
                value = get_data_method_info()
                self._upsert_method_cache(cache_key, value, '随机测试数据方法缓存')
                result[item_type] = {
                    'status': True,
                    'cache_key': cache_key,
                    'value': value,
                }
            elif item_type == 'api_assertion':
                value = assertion_func_info
                self._upsert_method_cache(cache_key, value, 'API断言方法缓存')
                result[item_type] = {
                    'status': True,
                    'cache_key': cache_key,
                    'value': value,
                }
            elif item_type == 'ui_operation':
                from mangotools.contracts import SocketCommandContract, SocketEnvelopeContract

                username = self._get_request_username(request)
                try:
                    SocketMessageService.send_socket_data(SocketEnvelopeContract(
                        code=200,
                        msg='刷新执行器方法缓存',
                        user=username,
                        is_notice=ClientTypeEnum.ACTUATOR,
                        data=SocketCommandContract(
                            func_name=ServerToolsCommandEnum.REFRESH_METHOD_OPTIONS.value,
                            func_args={}
                        )
                    ))
                    status = True
                    message = '已通知执行器刷新方法缓存'
                except MangoServerError as error:
                    status = False
                    message = error.msg
                result[item_type] = {
                    'status': status,
                    'message': message,
                    'cache_key': cache_key,
                    'value': self._get_method_cache_value(cache_key),
                }

        return ResponseData.success(RESPONSE_MSG_0201, result)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def assertion_test(self, request: Request):
        """测试断言方法"""
        groups = request.data.get('assertions')
        if isinstance(groups, list):
            return ResponseData.success(
                (200, '断言执行完成'),
                self._execute_assertion_test_groups(groups),
            )
        method = (request.data.get('method') or '').strip()
        if not method:
            return ResponseData.fail(ASSERTION_METHOD_REQUIRED)
        if not self._find_assertion_method(method):
            return ResponseData.fail(RESPONSE_MSG_0060)

        actual = request.data.get('actual')
        expect = request.data.get('expect')
        try:
            message = ObtainAssertion(test_data=ObtainTestData()).ass(
                method=method,
                actual=actual,
                expect=expect,
            )
            return ResponseData.success((200, '断言执行完成'), {
                'status': True,
                'message': message or '断言通过',
            })
        except Exception as error:
            return ResponseData.success((200, '断言执行完成'), {
                'status': False,
                'message': str(error),
            })

    @action(methods=['post'], detail=False)
    @error_response('system')
    def set_debug_log(self, request: Request):
        """设置系统调试日志级别"""
        is_debug = request.data.get('is_debug')
        data = (
            LoggingLevelService.set_debug(is_debug)
            if is_debug is not None
            else {
                'is_debug': settings.IS_DEBUG_LOG,
                'level': settings.BUSINESS_LOG_LEVEL,
                'service': settings.MANGO_SERVICE_NAME,
                'instance': settings.MANGO_SERVICE_INSTANCE,
                'scope': 'current_process',
            }
        )
        return ResponseData.success(RESPONSE_MSG_0136, data=data)


class SystemShareViews(SystemViews):
    authentication_classes = []
