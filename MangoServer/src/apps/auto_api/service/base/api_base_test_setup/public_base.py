# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-30 12:34
# @Author : 毛鹏
import mimetypes
from typing import Optional

from src.apps.auto_api.models import ApiHeaders
from src.apps.auto_api.models import ApiPublic
from src.apps.auto_api.service.base.api_base_test_setup.base_request import BaseRequest
from src.apps.auto_system.models import TestObject
from src.apps.auto_system.service.factory import func_test_object_value, get_database_connection
from src.common.enums.api_enum import ApiPublicTypeEnum
from src.common.enums.tools_enum import StatusEnum, AutoTypeEnum
from src.common.exceptions import *
from src.common.tools.database import DatabaseConnection
from src.common.tools.obtain_test_data import ObtainTestData

mimetypes.init()


class PublicBase(BaseRequest):
    """全局变量设置"""

    def __init__(self, db_context=None):
        self.test_data = ObtainTestData()
        super().__init__(self.test_data)
        self.db_context = db_context
        self.test_object: Optional[None | TestObject] = None
        self.mysql_connect: Optional[None | DatabaseConnection] = None
        self.db_connections: dict[int | str, DatabaseConnection] = {}
        self.skip_auth_load = False
        self.headers: dict = {}
        self.is_headers = None
        self.is_test_object = None
        self.is_public = None

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
        scope_key = (project_product_id, test_env)
        if self.is_test_object == scope_key:
            return
        self.is_test_object = scope_key
        self.mysql_connect = None
        self.close_db_connections()
        self.test_object = func_test_object_value(test_env,
                                                  project_product_id,
                                                  AutoTypeEnum.API.value)
        self.test_data.set_cache('url', self.test_object.value)
        log.api.debug(
            f'初始化测试对象，是否开启数据库的增删改权限：{self.test_object.db_c_status, self.test_object.db_c_status}')

    def get_db_connection(self, sql_item: dict | None = None, datasource_alias_id: int | str | None = None):
        if not self.test_object:
            raise ApiError(*ERROR_MSG_0046)
        alias_id = datasource_alias_id
        if alias_id is None and isinstance(sql_item, dict):
            alias_id = sql_item.get('datasource_alias') or sql_item.get('datasource_alias_id')
        if alias_id in ['', 'null', 'undefined']:
            alias_id = None
        cache_key = f'alias:{alias_id}' if alias_id else 'default'
        if cache_key not in self.db_connections:
            self.db_connections[cache_key] = get_database_connection(
                self.test_object,
                datasource_alias_id=int(alias_id) if alias_id else None,
                db_context=self.db_context,
            )
        if cache_key == 'default':
            self.mysql_connect = self.db_connections[cache_key]
        return self.db_connections[cache_key]

    def close_db_connections(self):
        if self.db_context:
            self.db_connections = {}
            self.mysql_connect = None
            return
        for connection in self.db_connections.values():
            close_all = getattr(connection, 'close_all', None)
            if callable(close_all):
                close_all()
            else:
                connection.close()
        self.db_connections = {}

    def init_public(self, project_product_id, test_env):
        scope_key = (project_product_id, test_env)
        if self.is_public == scope_key:
            return
        self.is_public = scope_key
        api_public = ApiPublic.objects.filter(
            status=StatusEnum.SUCCESS.value,
            project_product=project_product_id,
            test_env=test_env,
        ).order_by('type', 'test_env', 'id')
        log.api.debug(f'开始初始化全局变量！')
        for i in api_public:
            if i.type == ApiPublicTypeEnum.SQL.value:
                self.__sql(i)
            elif i.type == ApiPublicTypeEnum.CUSTOM.value:
                self.__custom(i)
        if not self.skip_auth_load:
            from src.apps.auto_api.service.base.api_base_test_setup.auth_manager import ApiAuthManager
            ApiAuthManager.load(project_product_id, test_env, self)

    def __custom(self, api_public_obj: ApiPublic):
        log.api.debug(f'全局变量-1->key：{api_public_obj.key}，value：{api_public_obj.value}')
        self.test_data.set_cache(api_public_obj.key, api_public_obj.value)

    def __sql(self, api_public_obj: ApiPublic):
        sql = self.test_data.replace(api_public_obj.value)
        result_list: list[dict] = self.get_db_connection(
            datasource_alias_id=api_public_obj.datasource_alias_id
        ).condition_execute(sql)
        log.api.debug(f'全局变量-2->key：{api_public_obj.key}，value:{sql}，查询结果：{result_list}')
        if isinstance(result_list, list) and len(result_list) > 0:
            self.test_data.set_sql_cache(api_public_obj.key, result_list[0])
            if not result_list:
                raise ApiError(*ERROR_MSG_0033, value=(sql,))

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
                raise ApiError(*ERROR_MSG_0040)
        return original_dict
