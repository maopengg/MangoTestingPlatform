# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-30 12:34
# @Author : 毛鹏
from typing import Optional
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiPublic, ApiInfo
from PyAutoTest.auto_test.auto_api.service.base_tools.base_request import BaseRequest
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_user.tools.factory import func_mysql_config, func_test_object_value
from PyAutoTest.enums.api_enum import ApiPublicTypeEnum, MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum, AutoTypeEnum
from PyAutoTest.exceptions import *
from PyAutoTest.models.api_model import RequestDataModel
from PyAutoTest.tools.obtain_test_data import ObtainTestData
from mangokit import MysqlConnect, MangoKitError


class CaseBase(ObtainTestData, BaseRequest):

    def __init__(self,
                 user_id: int,
                 test_env: int,
                 tasks_id: int = None,
                 is_send: bool = False):
        ObtainTestData.__init__(self)
        BaseRequest.__init__(self)
        self.user_id = user_id
        self.test_env = test_env
        self.tasks_id = tasks_id
        self.is_send = is_send

        self.project_product_id = None

        self.status = StatusEnum.SUCCESS
        self.error_message = None

        self.test_object: Optional[None | TestObject] = None
        self.mysql_connect: Optional[None | MysqlConnect] = None

    def init_test_object(self):
        self.test_object = func_test_object_value(self.test_env,
                                                  self.project_product_id,
                                                  AutoTypeEnum.API.value)
        if StatusEnum.SUCCESS.value in [self.test_object.db_c_status, self.test_object.db_rud_status]:
            self.mysql_connect = MysqlConnect(
                func_mysql_config(self.test_object.id),
                bool(self.test_object.db_c_status),
                bool(self.test_object.db_rud_status)
            )

    def init_public(self):
        api_public = ApiPublic.objects \
            .filter(status=StatusEnum.SUCCESS.value,
                    project_product=self.project_product_id) \
            .order_by('type')
        for i in api_public:
            if i.type == ApiPublicTypeEnum.SQL.value:
                self.__sql(i)
            elif i.type == ApiPublicTypeEnum.LOGIN.value:
                self.__login(i)
            elif i.type == ApiPublicTypeEnum.CUSTOM.value:
                self.__custom(i)
            elif i.type == ApiPublicTypeEnum.HEADERS.value:
                self.__headers(i)

    def request_data_clean(self, request_data_model: RequestDataModel) -> RequestDataModel:
        try:
            for key, value in request_data_model:
                if key == 'headers' and isinstance(value, str):
                    value = self.replace(value)
                    # if value == '${headers}':
                    #     value = None
                    if value and isinstance(value, str):
                        value = self.loads(value) if value else value
                    setattr(request_data_model, key, value)
                elif key == 'file':
                    if request_data_model.file:
                        file = []
                        for i in request_data_model.file:
                            i: dict = i
                            for k, v in i.items():
                                file_name = self.identify_parentheses(v)[0].replace('(', '').replace(')', '')
                                path = self.replace(v)
                                file.append((k, (file_name, open(path, 'rb'))))
                        request_data_model.file = file
                else:
                    value = self.replace(value)
                    setattr(request_data_model, key, value)

                if key == 'headers' and hasattr(self, 'headers') and self.headers:
                    new_dict = self.replace(self.headers)
                    if new_dict and isinstance(new_dict, str):
                        new_dict = self.loads(new_dict) if new_dict else new_dict
                    request_data_model.headers = self.__merge_dicts(request_data_model.headers, new_dict)
        except MangoKitError as error:
            raise ApiError(error.code, error.msg)
        return request_data_model

    async def __login(self, api_public_obj: ApiPublic):
        key = api_public_obj.key
        value_dict = self.load(api_public_obj.value)
        api_info = ApiInfo.objects.get(id=value_dict.get('api_info_id'))
        request_data_model = self.request_data_clean(RequestDataModel(method=MethodEnum(api_info.method).name,
                                                                      url=urljoin(self.test_object.value, api_info.url),
                                                                      headers=api_info.header,
                                                                      params=api_info.params,
                                                                      data=api_info.data,
                                                                      json_data=api_info.json,
                                                                      file=api_info.file))

        response = await self.http(request_data_model)
        if response.response_json is None:
            raise ApiError(*ERROR_MSG_0003)
        value = self.get_json_path_value(response.response_json, value_dict.get('json_path'))
        self.set_cache(key, value)

    def __custom(self, api_public_obj: ApiPublic):
        self.set_cache(api_public_obj.key, api_public_obj.value)

    def __headers(self, api_public_obj: ApiPublic):
        value = self.replace(api_public_obj.value)
        self.set_cache(api_public_obj.key, value)

    def __sql(self, api_public_obj: ApiPublic):
        if self.mysql_connect:
            result_list: list[dict] = self.mysql_connect.condition_execute(self.replace(api_public_obj.value))
            if isinstance(result_list, list):
                for result in result_list:
                    try:
                        for value, key in zip(result, eval(api_public_obj.key)):
                            self.set_cache(key, result.get(value))
                    except SyntaxError:
                        raise ToolsError(*ERROR_MSG_0035)
                if not result_list:
                    raise ToolsError(*ERROR_MSG_0033, value=(api_public_obj.value,))

    @classmethod
    def __merge_dicts(cls, base_dict, new_dict):
        if base_dict:
            result = base_dict.copy()
            for key, value in new_dict.items():
                if key not in result:
                    result[key] = value
            return result
        else:
            return new_dict
