# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-30 12:34
# @Author : 毛鹏
import logging
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiPublic, ApiInfo
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.service.get_database import GetDataBase
from PyAutoTest.enums.api_enum import ApiPublicTypeEnum, MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions.api_exception import LoginError
from PyAutoTest.exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.data_processor import DataProcessor
from PyAutoTest.tools.mysql_tools.mysql_control import MysqlConnect
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0003, ERROR_MSG_0033, ERROR_MSG_0035
from .http_request import HTTPRequest

log = logging.getLogger('api')


class CommonParameters(DataProcessor):

    def __init__(self, project_id: int, test_obj_id: int):
        super().__init__(project_id)
        self.project_id = project_id
        self.test_obj_id = test_obj_id
        # 获取测试环境对象
        self.test_object = TestObject.objects.get(id=self.test_obj_id)
        self.mysql_connect = None
        if StatusEnum.SUCCESS.value in [self.test_object.db_c_status, self.test_object.db_rud_status]:
            self.mysql_connect = MysqlConnect(GetDataBase.get_mysql_config(self.test_obj_id),
                                              bool(self.test_object.db_c_status),
                                              bool(self.test_object.db_rud_status)
                                              )
        self.api_public = ApiPublic.objects.filter(status=StatusEnum.SUCCESS.value,
                                                   project=project_id).order_by('type')
        for i in self.api_public:
            if i.type == ApiPublicTypeEnum.SQL.value:
                self.__sql(i)
            elif i.type == ApiPublicTypeEnum.LOGIN.value:
                self.__login(i)
            elif i.type == ApiPublicTypeEnum.CUSTOM.value:
                self.__custom(i)
            elif i.type == ApiPublicTypeEnum.HEADERS.value:
                self.__headers(i)

    def __login(self, api_public_obj: ApiPublic):
        key = api_public_obj.key
        value_dict = self.load(api_public_obj.value)
        api_info = ApiInfo.objects.get(id=value_dict.get('api_info_id'))
        request_data_model = self.request_data(RequestDataModel(method=MethodEnum(api_info.method).name,
                                                                url=urljoin(self.test_object.value, api_info.url),
                                                                headers=api_info.header,
                                                                params=api_info.params,
                                                                data=api_info.data,
                                                                json_data=api_info.json,
                                                                file=api_info.file))
        response: ResponseDataModel = HTTPRequest.http(request_data_model)
        if response.response_json is None:
            raise LoginError(*ERROR_MSG_0003)
        value = self.get_json_path_value(response.response_json, value_dict.get('json_path'))
        self.set_cache(key, value)

    def __custom(self, api_public_obj: ApiPublic):
        self.set_cache(api_public_obj.key, api_public_obj.value)

    def __headers(self, api_public_obj: ApiPublic):
        value = self.replace(api_public_obj.value)
        self.set_cache(api_public_obj.key, value)

    def __sql(self, api_public_obj: ApiPublic):
        """
        @需要重新写，不需要重新创建mysql连接对象
        @param api_public_obj:
        @return:
        """
        if self.mysql_connect:
            result_list: list[dict] = self.mysql_connect.condition_execute(self.replace(api_public_obj.value))
            if isinstance(result_list, list):
                for result in result_list:
                    try:
                        for value, key in zip(result, eval(api_public_obj.key)):
                            self.set_cache(key, result.get(value))
                    except SyntaxError:
                        raise SyntaxErrorError(*ERROR_MSG_0035)
                if not result_list:
                    raise MysqlQueryIsNullError(*ERROR_MSG_0033, value=(api_public_obj.value,))
