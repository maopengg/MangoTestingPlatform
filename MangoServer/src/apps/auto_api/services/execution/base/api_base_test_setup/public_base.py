# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-30 12:34
# @Author : 毛鹏
import mimetypes
import json
from dataclasses import dataclass
from copy import deepcopy
from functools import partial
from typing import Any

from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.exceptions import (
    API_PUBLIC_DATA_SOURCE_SQL_DATABASE_VARIABLE_EXECUTION_NOT_ALLOWED,
    AUTO_API_BASE_API_BASE_TEST_SETUP_PUBLIC_BASE_CODE_VARIABLE_INVALID,
    AUTO_API_BASE_API_BASE_TEST_SETUP_PUBLIC_BASE_CODE_VARIABLE_INVALID_CODE_CODE_VARIABLE_INVALID,
    AUTO_API_CODE_VARIABLE_RESULT_EMPTY,
    AutoApiError,
    API_GLOBAL_SQL_NO_RESULT,
    API_HEADER_KEY_JSON_INVALID,
    API_TEST_OBJECT_CONFIG_NOT_FOUND,
    API_CODE_VARIABLE_FUNCTION_INVALID,
    API_AUTH_CONTEXT_MISMATCH,
)
from src.apps.auto_api.models import ApiHeaders
from src.apps.auto_api.models import ApiPublic
from src.apps.auto_api.services.api_case.global_variable import ApiCaseGlobalVariableService
from src.apps.auto_api.services.execution.base.api_base_test_setup.base_request import BaseRequest
from src.apps.auto_api.services.execution.base.data_source_operation import cache_data_source_result, execute_data_source_query
from src.apps.data_factory.services.datasource.data_source_execution import DataSourceExecutionService
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.models import TestObject
from src.apps.test_center.services.datasource.factory import func_test_object_value
from src.apps.test_center.services.environment.test_target import TestTargetService
from src.common.logging import log
from src.common.testing import ObtainTestData

mimetypes.init()


@dataclass
class ApiPublicCodeContext:
    test_data: Any
    test_env: int
    project_product_id: int
    test_object: TestObject | None = None
    execute_data_source: Any = None


class PublicBase(BaseRequest):
    """全局变量设置"""

    def __init__(self, db_context=None):
        self.test_data = ObtainTestData()
        super().__init__(self.test_data)
        self.db_context = db_context
        self.test_object: TestObject | None = None
        self.skip_auth_load = False
        self.current_api_info_id = None
        self.headers: dict = {}
        self.is_headers = None
        self.is_test_object = None
        self.is_public = None
        self._failed_public_scopes = set()
        self.mcp_session_manager = None
        self.grpc_channel_manager = None
        self.target_auth_scope = None
        self._auth_context_signature = None
        self._auth_injected_cache = {}
        self._public_injected_cache = {}
        self.automation_type = AutoTypeEnum.API.value

    def init_headers(self, project_product_id: int):
        if self.is_headers == project_product_id:
            return
        self.is_headers = project_product_id
        self.headers = {}
        if self.headers != {}:
            return self.headers
        api_headers = {}
        for i in ApiHeaders.objects.filter(
                project_product_id=project_product_id,
                status=StatusEnum.SUCCESS.value):
            api_headers[i.key] = i.value
        self.update_dict_case_insensitive(self.headers, api_headers)
        return self.headers

    def init_test_object(self, project_product_id, test_env: int):
        scope_key = (project_product_id, test_env, self.automation_type)
        if self.is_test_object == scope_key:
            return
        self.clear_auth_injections(force=True)
        self.clear_public_injections()
        self._auth_context_signature = None
        self.target_auth_scope = None
        self.is_public = None
        self.is_test_object = None
        self.test_object = None
        self.test_data.delete_cache('url')
        self.close_db_connections()
        self.test_object = func_test_object_value(test_env,
                                                  project_product_id,
                                                  self.automation_type)
        if self.test_object.value or not (getattr(self.test_object, 'target_config', {}) or {}).get('selector'):
            self.test_data.set_cache('url', TestTargetService.resolve(self.test_object, self.test_data))
        self.is_test_object = scope_key
        log.api.debug(f'初始化测试对象：{self.test_object.id}')

    def execute_data_source(
            self,
            datasource_alias_id: int | str,
            operation_config,
            *,
            source_context: dict | None = None,
    ):
        if not self.test_object:
            raise AutoApiError(API_TEST_OBJECT_CONFIG_NOT_FOUND)
        return DataSourceExecutionService.execute(
            datasource_alias_id=datasource_alias_id,
            project_product_id=self.test_object.project_product_id,
            test_env=self.test_object.environment,
            operation_config=operation_config,
            source_context=source_context or {
                'source_type': 'api_custom_code',
                'source_stage': 'custom_code',
                'api_info_id': getattr(self, 'current_api_info_id', None),
            },
        )

    def close_db_connections(self):
        # 数据源执行服务按次管理连接，保留方法兼容现有用例收尾调用。
        return None

    def close_mcp_sessions(self):
        if self.mcp_session_manager is None:
            return
        try:
            self.mcp_session_manager.close()
        finally:
            self.mcp_session_manager = None

    def close_grpc_channels(self):
        if self.grpc_channel_manager is None:
            return
        try:
            self.grpc_channel_manager.close()
        finally:
            self.grpc_channel_manager = None

    @staticmethod
    def normalize_id_list(value) -> list[int]:
        return ApiCaseGlobalVariableService.normalize_id_list(value)

    def init_public(self, project_product_id, test_env, front_public_ids=None, front_auth_config_ids=None):
        front_public_ids = self.normalize_id_list(front_public_ids)
        front_auth_config_ids = self.normalize_id_list(front_auth_config_ids)
        scope_key = (project_product_id, test_env, tuple(front_public_ids), tuple(front_auth_config_ids))
        if self.is_public == scope_key:
            return
        self.target_auth_scope = (project_product_id, test_env, front_auth_config_ids, self.current_api_info_id)
        before = deepcopy(self.test_data.get_all())
        completed = False
        try:
            api_public = ApiCaseGlobalVariableService.list_public(project_product_id, test_env, front_public_ids)
            log.api.debug(f'开始初始化全局变量！')
            for i in api_public:
                if i.type == ApiPublicTypeEnum.SQL.value:
                    self.__sql(i, test_env)
                elif i.type == ApiPublicTypeEnum.CUSTOM.value:
                    self.__custom(i)
                elif i.type == ApiPublicTypeEnum.CODE.value:
                    self.__code(i, project_product_id, test_env)
            completed = True
        finally:
            after = self.test_data.get_all()
            for key in before.keys() | after.keys():
                if (key in before) != (key in after) or before.get(key) != after.get(key):
                    self._public_injected_cache.setdefault(key, (key in before, before.get(key)))
            if not completed:
                self._failed_public_scopes.add(scope_key)
                self.clear_public_injections()
                self.target_auth_scope = None
                self.is_public = None
                self.test_data.delete_cache('url')
        self.is_public = scope_key
        self._failed_public_scopes.discard(scope_key)

    def init_public_for_cleanup(self, project_product_id, test_env, front_public_ids=None, front_auth_config_ids=None):
        scope_key = (
            project_product_id, test_env,
            tuple(self.normalize_id_list(front_public_ids)),
            tuple(self.normalize_id_list(front_auth_config_ids)),
        )
        if scope_key in self._failed_public_scopes:
            # 清理只能使用已经取得的执行证据，不能重跑失败前置来重新发现或创建目标。
            log.api.warning(
                '后置不重复执行本轮已失败的公共变量初始化：product=%s env=%s public_ids=%s；'
                '仍按现有缓存执行原后置，缺失清理标识会明确报错，工厂清理继续执行',
                project_product_id, test_env, list(scope_key[2]),
            )
            return
        self.init_public(project_product_id, test_env, front_public_ids, front_auth_config_ids)

    def clear_public_injections(self):
        # 仅撤销产品配置注入的键；步骤响应提取等运行数据继续用于跨产品传值。
        for key, (existed, previous) in self._public_injected_cache.items():
            if existed:
                self.test_data.set_cache(key, previous)
            else:
                self.test_data.delete_cache(key)
        self._public_injected_cache.clear()

    def product_cache_keys(self) -> list[str]:
        return sorted({'url'} | self._public_injected_cache.keys() | self._auth_injected_cache.keys())

    def clear_auth_injections(self, *, force=False):
        current = self.test_data.get_all()
        for key, (existed, previous, injected) in self._auth_injected_cache.items():
            # 前置明确改写的值属于调用方，不随旧授权一起撤销。
            if not force and (key not in current or current[key] != injected):
                continue
            if existed:
                self.test_data.set_cache(key, previous)
            else:
                self.test_data.delete_cache(key)
        self._auth_injected_cache.clear()

    def ensure_execution_context(self):
        if not self.test_object:
            raise AutoApiError(API_TEST_OBJECT_CONFIG_NOT_FOUND)
        target = self.test_object
        try:
            address = TestTargetService.resolve(target, self.test_data)
        except Exception:
            self.clear_auth_injections()
            self._auth_context_signature = None
            self.test_data.delete_cache('url')
            raise
        self.test_data.set_cache('url', address)
        if self.skip_auth_load or not self.target_auth_scope:
            return
        rules = getattr(target, 'target_config', {}) or {}
        selector = rules.get('selector', '') if not target.value else ''

        def signature():
            return json.dumps([
                target.project_product_id, target.environment, getattr(target, 'id', None),
                TestTargetService.resolve(target, self.test_data), selector,
                self.test_data.get_cache(selector) if selector else None, self.target_auth_scope,
            ], ensure_ascii=False, sort_keys=True)

        from src.apps.auto_api.services.execution.base.api_base_test_setup.auth_manager import ApiAuthManager
        previous_api_info_id = self.current_api_info_id
        try:
            current_signature = signature()
            if current_signature != self._auth_context_signature:
                self.clear_auth_injections()
                # 旧授权撤销可能恢复此前遮盖的路由变量，必须重新解析。
                address = TestTargetService.resolve(target, self.test_data)
                self.test_data.set_cache('url', address)
                current_signature = signature()
            self.current_api_info_id = self.target_auth_scope[3]
            ApiAuthManager.load(self.target_auth_scope[0], self.target_auth_scope[1], self, self.target_auth_scope[2])
            if signature() != current_signature:
                raise AutoApiError(API_AUTH_CONTEXT_MISMATCH)
            self._auth_context_signature = current_signature
            self.test_data.set_cache('url', address)
        except Exception:
            self.clear_auth_injections()
            self._auth_context_signature = None
            self.test_data.delete_cache('url')
            raise
        finally:
            self.current_api_info_id = previous_api_info_id

    def __custom(self, api_public_obj: ApiPublic):
        log.api.debug(f'全局变量-1->key：{api_public_obj.key}，value：{api_public_obj.value}')
        self.test_data.set_cache(api_public_obj.key, api_public_obj.value)

    def __sql(self, api_public_obj: ApiPublic, test_env: int):

        DataFactoryDatasourceResolver.require_sql_public_alias(
            api_public_obj.datasource_alias,
            api_public_obj.project_product_id,
        )
        execution_result = execute_data_source_query(
            self,
            test_env,
            {
                'datasource_alias': api_public_obj.datasource_alias_id,
                'value': api_public_obj.value,
            },
            write_error=API_PUBLIC_DATA_SOURCE_SQL_DATABASE_VARIABLE_EXECUTION_NOT_ALLOWED,
            operation_name='SQL全局变量查询语句',
            source_context={
                'source_type': 'api_global_variable',
                'source_stage': 'global_variable',
                'source_id': getattr(api_public_obj, 'id', None),
                'global_variable_id': getattr(api_public_obj, 'id', None),
                'api_info_id': getattr(self, 'current_api_info_id', None),
            },
        )
        if not cache_data_source_result(self, api_public_obj.key, execution_result):
            raise AutoApiError(API_GLOBAL_SQL_NO_RESULT, value=(api_public_obj.value,))
        log.api.debug(
            f'全局变量-2->key：{api_public_obj.key}，'
            f'逻辑数据源：{api_public_obj.datasource_alias_id}，查询成功'
        )

    def __code(self, api_public_obj: ApiPublic, project_product_id: int, test_env: int):
        context = ApiPublicCodeContext(
            test_data=self.test_data,
            test_env=test_env,
            project_product_id=project_product_id,
            test_object=self.test_object,
            execute_data_source=partial(
                self.execute_data_source,
                source_context={
                    'source_type': 'api_global_variable',
                    'source_stage': 'custom_code',
                    'source_id': getattr(api_public_obj, 'id', None),
                    'global_variable_id': getattr(api_public_obj, 'id', None),
                    'api_info_id': getattr(self, 'current_api_info_id', None),
                },
            ),
        )
        namespace = {}
        try:
            exec(api_public_obj.value, namespace)
        except Exception as error:
            raise AutoApiError(API_CODE_VARIABLE_FUNCTION_INVALID, value=(api_public_obj.name, str(error))) from error
        variable_func = namespace.get('variable')
        if not callable(variable_func):
            raise AutoApiError(AUTO_API_BASE_API_BASE_TEST_SETUP_PUBLIC_BASE_CODE_VARIABLE_INVALID,
                               value=(api_public_obj.name,))
        try:
            result = variable_func(context)
        except Exception as error:
            raise AutoApiError(API_CODE_VARIABLE_FUNCTION_INVALID, value=(api_public_obj.name, str(error))) from error
        if not isinstance(result, dict):
            raise AutoApiError(
                AUTO_API_BASE_API_BASE_TEST_SETUP_PUBLIC_BASE_CODE_VARIABLE_INVALID_CODE_CODE_VARIABLE_INVALID,
                value=(api_public_obj.name,))
        cache_data = {key: value for key, value in result.items() if value is not None}
        if not cache_data:
            raise AutoApiError(AUTO_API_CODE_VARIABLE_RESULT_EMPTY, value=(api_public_obj.name,))
        for key, value in cache_data.items():
            self.test_data.set_cache(key, value)
        log.api.debug(f'全局变量-3->name：{api_public_obj.name}，keys：{list(cache_data.keys())}')

    @staticmethod
    def update_dict_case_insensitive(original_dict: dict[str], new_dict: dict[str]):
        original_lower_keys = {k.lower(): k for k in original_dict.keys()}
        for new_key, new_value in new_dict.items():
            new_key_lower = new_key.lower()
            if new_key_lower in original_lower_keys:
                original_key = original_lower_keys[new_key_lower]
                del original_dict[original_key]
            if isinstance(new_key, str) and isinstance(new_value, str):
                original_dict[new_key] = new_value.strip()
                original_lower_keys[new_key_lower] = new_key
            else:
                raise AutoApiError(API_HEADER_KEY_JSON_INVALID)
        return original_dict
