# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-11-30 12:34
# @Author : 毛鹏
import mimetypes
from typing import Optional

from mangotools.database import MysqlConnect
from src.auto_test.auto_api.models import ApiHeaders
from src.auto_test.auto_api.models import ApiPublic
from src.auto_test.auto_api.service.base.api_base_test_setup.base_request import BaseRequest
from src.auto_test.auto_system.models import TestObject
from src.auto_test.auto_user.tools.factory import func_mysql_config, func_test_object_value
from src.enums.api_enum import ApiPublicTypeEnum
from src.enums.tools_enum import StatusEnum, AutoTypeEnum
from src.exceptions import *
from src.tools.obtain_test_data import ObtainTestData

mimetypes.init()


class PublicBase(BaseRequest):
    """公共参数设置"""

    def __init__(self):
        self.test_data = ObtainTestData()
        super().__init__(self.test_data)
        self.test_object: Optional[None | TestObject] = None
        self.mysql_connect: Optional[None | MysqlConnect] = None
        self.headers: dict = {}
        self.is_headers = None
        self.is_test_object = None
        self.is_public = None

    def init_headers(self, project_product_id: int):
        if self.is_headers == project_product_id:
            return
        self.is_headers = project_product_id
        if self.headers != {}:
            return self.headers
        for i in ApiHeaders.objects.filter(
                project_product_id=project_product_id,
                status=StatusEnum.SUCCESS.value):
            self.headers[i.key] = i.value
        return self.headers

    def init_test_object(self, project_product_id, test_env: int):
        if self.is_test_object == project_product_id:
            return
        self.is_test_object = project_product_id
        self.test_object = func_test_object_value(test_env,
                                                  project_product_id,
                                                  AutoTypeEnum.API.value)
        self.test_data.set_cache('url', self.test_object.value)
        log.api.debug(
            f'初始化测试对象，是否开启数据库的增删改权限：{self.test_object.db_c_status, self.test_object.db_c_status}')
        if StatusEnum.SUCCESS.value in [self.test_object.db_c_status, self.test_object.db_rud_status]:
            self.mysql_connect = MysqlConnect(
                func_mysql_config(self.test_object.id),
                bool(self.test_object.db_c_status),
                bool(self.test_object.db_rud_status)
            )

    def init_public(self, project_product_id, test_env):
        if self.is_public == project_product_id:
            return
        self.is_public = project_product_id
        api_public = ApiPublic.objects.filter(
            status=StatusEnum.SUCCESS.value,
            project_product=project_product_id) \
            .order_by('type')
        log.api.debug(f'开始初始化公共参数！')
        for i in api_public:
            if i.type == ApiPublicTypeEnum.SQL.value:
                self.__sql(i)
            elif i.type == ApiPublicTypeEnum.LOGIN.value:
                self.api_request(i.value, test_env)
            elif i.type == ApiPublicTypeEnum.CUSTOM.value:
                self.__custom(i)

    def __custom(self, api_public_obj: ApiPublic):
        log.api.debug(f'公共参数-1->key：{api_public_obj.key}，value：{api_public_obj.value}')
        self.test_data.set_cache(api_public_obj.key, api_public_obj.value)

    def __sql(self, api_public_obj: ApiPublic):
        if self.mysql_connect:
            sql = self.test_data.replace(api_public_obj.value)
            result_list: list[dict] = self.mysql_connect.condition_execute(sql)
            log.api.debug(f'公共参数-2->key：{api_public_obj.key}，value:{sql}，查询结果：{result_list}')
            if isinstance(result_list, list) and len(result_list) > 0:
                self.test_data.set_sql_cache(api_public_obj.key, result_list[0])
                if not result_list:
                    raise ToolsError(*ERROR_MSG_0033, value=(sql,))
