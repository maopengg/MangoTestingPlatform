# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-30 12:34
# @Author : 毛鹏
from typing import Optional
from urllib.parse import urljoin

from mangokit import MysqlConnect, MangoKitError
from src.auto_test.auto_api.models import ApiHeaders
from src.auto_test.auto_api.models import ApiPublic, ApiInfo
from src.auto_test.auto_api.service.base_tools.base_request import BaseRequest
from src.auto_test.auto_system.models import TestObject
from src.auto_test.auto_user.tools.factory import func_mysql_config, func_test_object_value
from src.enums.api_enum import ApiPublicTypeEnum, MethodEnum
from src.enums.tools_enum import StatusEnum, AutoTypeEnum
from src.exceptions import *
from src.models.api_model import RequestModel, ResponseModel
from src.tools.obtain_test_data import ObtainTestData


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

    def init_headers(self):
        headers = {}
        for i in ApiHeaders.objects.filter(
                project_product_id=self.project_product_id,
                status=StatusEnum.SUCCESS.value):
            headers[i.key] = i.value
        return headers

    def init_test_object(self, ):
        self.test_object = func_test_object_value(self.test_env,
                                                  self.project_product_id,
                                                  AutoTypeEnum.API.value)
        if StatusEnum.SUCCESS.value in [self.test_object.db_c_status, self.test_object.db_rud_status]:
            self.mysql_connect = MysqlConnect(
                func_mysql_config(self.test_object.id),
                bool(self.test_object.db_c_status),
                bool(self.test_object.db_rud_status)
            )

    def init_public(self, project_product_id):
        api_public = ApiPublic.objects \
            .filter(status=StatusEnum.SUCCESS.value,
                    project_product=project_product_id) \
            .order_by('type')
        for i in api_public:
            if i.type == ApiPublicTypeEnum.SQL.value:
                self.__sql(i)
            elif i.type == ApiPublicTypeEnum.LOGIN.value:
                self.api_request(i.value)
            elif i.type == ApiPublicTypeEnum.CUSTOM.value:
                self.__custom(i)

    def request_data_clean(self, request_data_model: RequestModel) -> RequestModel:
        try:
            for key, value in request_data_model:
                if key == 'headers':
                    value = self.replace(value)
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
        except MangoKitError as error:
            raise ApiError(error.code, error.msg)
        return request_data_model

    def api_request(self, api_info_id: int, request_model: RequestModel = None, is_error=True) -> ResponseModel:
        api_info = ApiInfo.objects.get(id=api_info_id)
        self.project_product_id = api_info.project_product.id
        self.init_test_object()
        if request_model is None:
            request_model = self.request_data_clean(RequestModel(
                method=MethodEnum(api_info.method).name,
                url=urljoin(self.test_object.value, api_info.url),
                headers=api_info.header if api_info.header else self.init_headers(),
                params=api_info.params,
                data=api_info.data,
                json=api_info.json,
                file=api_info.file))
        response = self.http(request_model)
        try:
            if api_info.posterior_re:
                self.api_info_posterior_json_re(api_info.posterior_re, response)
            if api_info.posterior_json_path:
                self.api_info_posterior_json_path(api_info.posterior_json_path, response)
            if api_info.posterior_func:
                self.analytic_func(api_info.posterior_func)(self, response)
        except MangoKitError as error:
            if is_error:
                raise ApiError(error.code, error.msg)
        except Exception as error:
            log.api.error(f'api_info的请求失败，api_id:{api_info_id}, error:{error}')
            if is_error:
                raise error
        return response

    def __custom(self, api_public_obj: ApiPublic):
        self.set_cache(api_public_obj.key, api_public_obj.value)

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

    def api_info_posterior_json_path(self, posterior_json_path: list[dict], response: ResponseModel):
        if response.json is None:
            raise ApiError(*ERROR_MSG_0023)
        for i in posterior_json_path:
            print(i.get('key'), response.json, i.get('value'))
            self.set_cache(i.get('key'), self.get_json_path_value(response.json, i.get('value')))

    def api_info_posterior_json_re(self, posterior_re: str, response: ResponseModel):
        pass

    @staticmethod
    def analytic_func(func_str, func_name='func'):
        try:
            global_namespace = {}
            exec(func_str, global_namespace)
            return global_namespace[func_name]
        except (KeyError, SyntaxError, TypeError) as error:
            log.api.warning(f'函数字符串：{func_str}')
            log.api.error(error)
            raise ToolsError(*ERROR_MSG_0014)
