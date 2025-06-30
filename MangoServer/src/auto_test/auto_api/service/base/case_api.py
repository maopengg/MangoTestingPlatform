# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json

import time
from mangotools.exceptions import MangoToolsError

from src.auto_test.auto_api.models import ApiCaseDetailedParameter
from src.auto_test.auto_api.service.base.case_data import ApiCaseBase
from src.enums.tools_enum import StatusEnum
from src.exceptions import *
from src.models.api_model import ResponseModel, RequestModel, AssResultModel


class CaseApiBase(ApiCaseBase):
    """ 测试用例详情的前后置+断言+缓存 """
    ass_result: list[AssResultModel] = []

    def front_main(self,
                   case_detailed_parameter: ApiCaseDetailedParameter,
                   request: RequestModel
                   ) -> RequestModel:
        if case_detailed_parameter.front_sql:
            self.__front_sql(case_detailed_parameter.front_sql)
        if case_detailed_parameter.front_func:
            request = self.__front_func(case_detailed_parameter.front_func, request)
        return request

    def ass_main(self,
                 response: ResponseModel,
                 case_detailed_parameter: ApiCaseDetailedParameter
                 ) -> list[AssResultModel]:
        self.ass_result = []
        try:
            if case_detailed_parameter.ass_jsonpath:
                ass_jsonpath = self.test_data.replace(case_detailed_parameter.ass_jsonpath)
                self.__ass_jsonpath(response.json, ass_jsonpath)
            if case_detailed_parameter.ass_sql:
                ass_sql = self.test_data.replace(case_detailed_parameter.ass_sql)
                self.__ass_sql(ass_sql)
            if case_detailed_parameter.ass_json_all:
                ass_json_all = self.test_data.replace(case_detailed_parameter.ass_json_all)
                self.__ass_json_all(response.json, ass_json_all)
            if case_detailed_parameter.ass_text_all:
                self.__ass_test_all(response.text, self.test_data.replace(case_detailed_parameter.ass_text_all))  # type: ignore
        except (ToolsError, ApiError) as error:
            self.status = StatusEnum.FAIL
            self.error_message = error.msg
        finally:
            return self.ass_result

    def posterior_main(self, response: ResponseModel,
                       case_detailed_parameter: ApiCaseDetailedParameter) -> ResponseModel:
        if case_detailed_parameter.posterior_response:
            self.__posterior_response(response.json,
                                      self.test_data.replace(case_detailed_parameter.posterior_response))
        if case_detailed_parameter.posterior_sql:
            self.__posterior_sql(self.test_data.replace(case_detailed_parameter.posterior_sql))
        if case_detailed_parameter.posterior_sleep:
            time.sleep(int(case_detailed_parameter.posterior_sleep))
        if case_detailed_parameter.posterior_func:
            response = self.__posterior_func(case_detailed_parameter.posterior_func, response)
        return response

    def __posterior_func(self, posterior_func: str, response: ResponseModel) -> RequestModel:
        try:
            log.api.debug(f'用例详情后置-3->函数：{posterior_func}')
            return self.analytic_func(posterior_func)(self, response)
        except (KeyError, MangoToolsError) as error:
            log.api.debug(f"数据报错，函数：{posterior_func}, request:{response.model_dump_json()}, error：{error}")
            raise ApiError(*ERROR_MSG_0013)

    def __posterior_sql(self, sql_list: list[dict]):
        if self.mysql_connect:
            for sql_obj in sql_list:
                sql = self.test_data.replace(sql_obj.get('key'))
                res = self.mysql_connect.condition_execute(sql)
                log.api.debug(f'用例详情后置-2->key：{sql_obj.get("value")}，sql：{sql}，结果：{res}')
                if isinstance(res, list) and len(res) > 0:
                    log.api.info(f'前置sql写入的数据：{sql_obj.get("value")},sql: {res[0]}')
                    self.test_data.set_sql_cache(sql_obj.get('value'), res[0])

    def __posterior_response(self, response_text: dict, posterior_response: list[dict]):
        for i in posterior_response:
            value = self.test_data.get_json_path_value(response_text, i['key'])
            log.api.debug(f'用例详情后置-1->key：{i["value"]}，value：{value}')
            self.test_data.set_cache(i['value'], value)

    def __ass_jsonpath(self, response_data, ass_jsonpath):
        _dict = {}
        method = None
        try:
            if ass_jsonpath:
                for i in ass_jsonpath:
                    value = self.test_data.get_json_path_value(response_data, i['actual'])
                    _dict = {'actual': str(value)}
                    if i.get('expect'):
                        try:
                            _dict['expect'] = str(eval(i.get('expect')))
                        except (NameError, SyntaxError):
                            _dict['expect'] = i.get('expect')
                    method = i.get('method')
                    log.api.debug(f'用例详情断言-3->方法：{method}，数据：{_dict}')
                    getattr(self, method)(**_dict)
        except AssertionError as error:
            log.api.debug(str(error))
            self.ass_result.append(AssResultModel(type=method, expect=_dict.get('expect'), actual=_dict.get('actual')))
            raise ApiError(*ERROR_MSG_0005)
        except ToolsError as error:
            log.api.debug(str(error))
            self.ass_result.append(AssResultModel(type=method, expect=_dict.get('expect'), actual=_dict.get('actual')))
            raise error

    def __ass_sql(self, sql_list: list[dict]):
        _dict = {'actual': None}
        method = None
        try:
            if self.mysql_connect:
                for sql in sql_list:
                    actual = self.mysql_connect.condition_execute(self.test_data.replace(sql.get('actual')))
                    if not actual:
                        raise ApiError(*ERROR_MSG_0041)
                    if isinstance(actual, list):
                        _dict = {'actual': str(list(actual[0].values())[0])}
                    if sql.get('expect'):
                        _dict['expect'] = sql.get('expect')
                    method = sql.get('method')
                    log.api.debug(f'用例详情断言-3->方法：{method}，数据：{_dict}')
                    getattr(self, method)(**_dict)
        except AssertionError as error:
            log.api.debug(str(error))
            self.ass_result.append(AssResultModel(type=method, expect=_dict.get('expect'), actual=_dict.get('actual')))
            raise ApiError(*ERROR_MSG_0006)

    def __ass_json_all(self, actual: dict, ass_json_all: dict):
        try:
            log.api.debug(f'用例详情断言-2->实际：{actual}，预期：{ass_json_all}')
            self.test_data.ass_response_whole(actual, ass_json_all)
        except AssertionError as error:
            log.api.debug(str(error))
            self.ass_result.append(AssResultModel(
                type='全匹配断言',
                expect=json.dumps(ass_json_all, ensure_ascii=False),
                actual=json.dumps(actual, ensure_ascii=False)
            ))
            raise ApiError(*ERROR_MSG_0004, value=(ass_json_all, actual))

    def __ass_test_all(self, actual: str, ass_test_all: str):
        try:
            log.api.debug(f'用例详情断言-1->实际：{actual}，预期：{ass_test_all}')
            assert actual.strip() == ass_test_all.strip()
        except AssertionError as error:
            log.api.debug(str(error))
            self.ass_result.append(AssResultModel(
                type='响应文本全匹配',
                expect=ass_test_all,
                actual=actual
            ))
            raise ApiError(*ERROR_MSG_0009, value=(ass_test_all, actual))

    def __front_sql(self, front_sql: list[str]):
        if self.mysql_connect and front_sql:
            for sql in front_sql:
                sql = self.test_data.replace(sql)
                res = self.mysql_connect.condition_execute(sql)
                log.api.debug(f'用例详情前置-1->sql：{sql}，查询结果：{res}')

    def __front_func(self, front_func: str, request: RequestModel) -> RequestModel:
        try:
            log.api.debug(f'用例详情前置-2->{front_func}')
            return self.analytic_func(front_func)(self, request)
        except (KeyError, MangoToolsError) as error:
            log.api.error(f"数据报错，函数：{front_func}, request:{request.model_dump_json()}, error：{error}")
            raise ApiError(*ERROR_MSG_0010)
