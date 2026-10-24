# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
import json

from django.core.cache import cache
from django.core.exceptions import FieldError
from django.db import ProgrammingError, transaction
from mangotools.enums import CacheValueTypeEnum
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.api.serializers.cache_data_mutation import CacheDataSerializers
from src.apps.system.enums import CacheDataKey2Enum, ClientTypeEnum
from src.apps.system.enums.cache import SystemConfigManagementLevelEnum
from src.apps.system.models import CacheData
from src.apps.system.services.system_config import (
    CONFIG_GROUP_TITLES,
    DEPRECATED_SYSTEM_CONFIG_GROUPS,
    SystemConfigService,
)
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0031,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0141,
    RESPONSE_MSG_0287,
    RESPONSE_MSG_0325,
)

SECRET_VALUE_MASK = "__KEEP_SECRET__"

from src.apps.system.api.serializers.cache_data import CacheDataSerializersC


class CacheDataCRUD(ModelCRUD):
    model = CacheData
    queryset = CacheData.objects.all()
    serializer_class = CacheDataSerializersC
    serializer = CacheDataSerializers
    page_permission_key = 'system.settings'

    @error_response('system')
    def get(self, request: Request):
        SystemConfigService.sync_registered_configs()
        books = self.model.objects.filter(
            is_enabled=True,
            management_level__gte=SystemConfigManagementLevelEnum.CAUTION.value,
        ).exclude(
            group__in=DEPRECATED_SYSTEM_CONFIG_GROUPS,
        ).order_by('group', '-management_level', 'sort', 'id')
        try:
            return ResponseData.success(RESPONSE_MSG_0001,
                                        self.serializer_class(instance=self.serializer_class.setup_eager_loading(books),
                                                              many=True).data,
                                        books.count())
        except FieldError:
            return ResponseData.success(RESPONSE_MSG_0001,
                                        self.serializer_class(instance=books,
                                                              many=True).data,
                                        books.count())

    @error_response('system')
    @transaction.atomic
    def put(self, request: Request):
        execution_validation_error = SystemConfigService.validate_execution_config_values({
            str(item.get('key')): item.get('value')
            for item in request.data
            if item.get('key')
        })
        if execution_validation_error:
            return ResponseData.fail(
                RESPONSE_MSG_0287,
                value=(execution_validation_error,),
            )
        for i in request.data:
            cache_data = self.__get_config(i)
            if cache_data.key == "EVALUATION_AI_PROFILES":
                from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
                i = {**i, "value": EvaluationAiProfileService.prepare_save(i.get("value"), cache_data.value)}
            if cache_data.management_level == SystemConfigManagementLevelEnum.INTERNAL.value:
                return ResponseData.fail(
                    RESPONSE_MSG_0287,
                    value=("一级系统内部配置不允许通过配置管理页面修改",),
                )
            validation_error = SystemConfigService.validate_editable_config(
                cache_data.key, i.get('value'),
            )
            if validation_error:
                return ResponseData.fail(RESPONSE_MSG_0287, value=(validation_error,))
            data = {
                **self.serializer(instance=cache_data).data,
                **i,
            }
            data['update_user'] = request.user.get('id') if isinstance(request.user, dict) else None
            if cache_data.is_secret and i.get('value') == SECRET_VALUE_MASK:
                data['value'] = cache_data.value
            else:
                data['value'] = self.__normalize_config_value(cache_data, data.get('value'))
            serializer = self.serializer(instance=cache_data, data=data)
            if serializer.is_valid():
                serializer.save()
                SystemConfigService.invalidate(cache_data.key)
                if cache_data.key == "API_WORKER_THREAD_POOL_SIZE":
                    SystemConfigService.normalize_api_worker_thread_pool_size()
                if cache_data.key == "DATA_FACTORY_VALIDATION_ENVIRONMENTS":
                    SystemConfigService.normalize_data_factory_validation_environments()
            else:
                return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)
        return ResponseData.success(RESPONSE_MSG_0082, )

    @staticmethod
    def __get_config(data):
        if data.get('id'):
            return CacheData.objects.select_for_update().get(pk=data.get('id'))
        return CacheData.objects.select_for_update().get(key=data.get('key'))

    @staticmethod
    def __normalize_config_value(cache_data: CacheData, value):
        if value is None:
            return None
        if cache_data.value_type == CacheValueTypeEnum.BOOL.value:
            return "true" if value in (True, "true", "True", "1", 1) else "false"
        if cache_data.value_type in (CacheValueTypeEnum.DICT.value, CacheValueTypeEnum.JSON.value,
                                     CacheValueTypeEnum.LIST.value):
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        return value


class CacheDataViews(ViewSet):
    model = CacheData
    serializer_class = CacheDataSerializers
    action_permission_map = {
        'grouped': 'system.settings',
        'get_key_value': 'system.settings',
        'clear_runtime_cache': 'system.settings:debug',
    }

    @error_response('system')
    @action(methods=['GET'], detail=False)
    def grouped(self, request: Request):
        SystemConfigService.sync_registered_configs()
        queryset = self.model.objects.filter(
            is_enabled=True,
            management_level__gte=SystemConfigManagementLevelEnum.CAUTION.value,
        ).exclude(
            group__in=DEPRECATED_SYSTEM_CONFIG_GROUPS,
        ).order_by('group', '-management_level', 'sort', 'id')
        grouped_data = {}
        for item in queryset:
            group_key = item.group or 'system'
            grouped_data.setdefault(group_key, {
                'key': group_key,
                'title': CONFIG_GROUP_TITLES.get(group_key, group_key),
                'items': [],
            })
            grouped_data[group_key]['items'].append(self.__serialize_item(item))
        data = list(grouped_data.values())
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @error_response('system')
    @action(methods=['GET'], detail=False)
    def get_key_value(self, request: Request):
        """
        获取系统配置值。兼容单 key 查询，也支持批量 keys/keys[] 查询。
        @param request:
        @return:
        """
        method_cache_keys = {
            CacheDataKey2Enum.TEST_DATA_SELECT_VALUE.value,
            CacheDataKey2Enum.ASS_SELECT_VALUE.value,
            CacheDataKey2Enum.SELECT_VALUE.value,
        }

        user_client_type = request.user.get('client_type') if isinstance(request.user, dict) else None
        is_actuator = (
                user_client_type == ClientTypeEnum.ACTUATOR.value
                and request.headers.get('Source-Type') == str(ClientTypeEnum.ACTUATOR.value)
        )

        def get_value(key: str):
            config = self.model.objects.filter(key=key).only('value', 'is_secret').first()
            if key == "EVALUATION_AI_PROFILES":
                from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
                return EvaluationAiProfileService.masked(config.value if config else [])
            if config and config.is_secret:
                if config.value in (None, ''):
                    return None
                return config.value if is_actuator else SECRET_VALUE_MASK
            default = {} if key in method_cache_keys else None
            return SystemConfigService.get(key, default=default)

        try:
            raw_keys = request.query_params.getlist('keys[]') or request.query_params.getlist('keys')
            keys = [
                key.strip()
                for item in raw_keys
                for key in str(item).split(',')
                if key.strip()
            ]
            if keys:
                data = {key: get_value(key) for key in keys}
                return ResponseData.success(RESPONSE_MSG_0031, data)
            value = get_value(request.query_params.get('key'))
        except ProgrammingError:
            return ResponseData.fail(RESPONSE_MSG_0141)
        return ResponseData.success(RESPONSE_MSG_0031, value)

    @error_response('system')
    @action(methods=['POST'], detail=False)
    def clear_runtime_cache(self, request: Request):
        cache.clear()
        return ResponseData.success(RESPONSE_MSG_0325)

    @staticmethod
    def __serialize_item(item):
        data = CacheDataSerializers(instance=item).data
        data['has_value'] = item.value not in (None, '')
        if item.is_secret:
            data['value'] = SECRET_VALUE_MASK if data['has_value'] else None
        if item.key == "EVALUATION_AI_PROFILES":
            from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
            data['value'] = EvaluationAiProfileService.masked(item.value)
        return data
