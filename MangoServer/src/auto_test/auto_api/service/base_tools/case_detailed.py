# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json

import time

from src.auto_test.auto_api.service.base_tools.api_case_data import ApiCaseData
from src.enums.tools_enum import StatusEnum
from src.exceptions import *
from src.models.api_model import ResponseDataModel, RequestDataModel, AssResultModel
from src.tools.assertion.public_assertion import PublicAssertion


class CaseDetailedInit(ApiCaseData, PublicAssertion):
    ass_result: list[AssResultModel] = []

    def send_request(self, request_data_model: RequestDataModel) -> tuple[RequestDataModel, ResponseDataModel]:
        response = self.http(request_data_model)
        log.api.debug(f'响应请求：{response.model_dump_json()}')
        return request_data_model, response

    def front_sql(self, case_detailed):
        if self.mysql_connect:
            for sql in case_detailed.front_sql:
                res = self.mysql_connect.condition_execute(sql)
                if isinstance(res, list):
                    for i in res:
                        for key, value in i.items():
                            self.set_cache(key, value)
                            log.api.info(f'前置sql写入的数据：{self.get_cache(key)}')

    def assertion(self, response: ResponseDataModel, case_detailed) -> list[AssResultModel]:
        if response.response_json:
            response_data = response.response_json
        else:
            try:
                response_data = eval(response.response_text)
            except SyntaxError:
                raise ApiError(*ERROR_MSG_0007)
            except ValueError:
                raise ApiError(*ERROR_MSG_0039)
        self.ass_result = []
        try:
            if case_detailed.ass_response_value:
                self.__assertion_response_value(response_data, self.replace(case_detailed.ass_response_value))
            if case_detailed.ass_sql:
                self.__assertion_sql(self.replace(case_detailed.ass_sql))
            if case_detailed.ass_response_whole:
                self.__assertion_response_whole(response_data, self.replace(case_detailed.ass_response_whole))
        except ApiError as error:
            self.status = StatusEnum.FAIL
            self.error_message = error.msg
        finally:
            return self.ass_result

    def posterior(self, response: ResponseDataModel, case_detailed):
        if case_detailed.posterior_response:
            self.__posterior_response(response.response_json, self.replace(case_detailed.posterior_response))
        if case_detailed.posterior_sql:
            self.__posterior_sql(self.replace(case_detailed.posterior_sql))
        if case_detailed.posterior_sleep:
            self.__posterior_sleep(self.replace(case_detailed.posterior_sleep))

    # def dump_data(self, case_detailed):
    #     if self.mysql_connect:
    #         for sql in case_detailed.dump_data:
    #             if sql.strip().lower().startswith('select'):
    #                 raise DumpDataError(*ERROR_MSG_0010)
    #             res = self.mysql_connect.condition_execute(self.replace(sql))
    #             if isinstance(res, int):
    #                 log.info(f'删除成功的条数：{res}')

    def __posterior_sql(self, sql_list: list[dict]):
        if self.mysql_connect:
            for sql_obj in sql_list:
                res = self.mysql_connect.condition_execute(sql_obj.get('key'))
                if isinstance(res, list):
                    for res_dict in res:
                        for key, value in res_dict.items():
                            self.set_cache(sql_obj.get('value'), str(value))
                            log.api.info(f'{sql_obj.get("value")}sql写入的数据：{self.get_cache(sql_obj.get("value"))}')

    def __posterior_response(self, response_text: dict, posterior_response: list[dict]):
        for i in posterior_response:
            value = self.get_json_path_value(response_text, i['key'])
            self.set_cache(i['value'], value)

    @classmethod
    def __posterior_sleep(cls, sleep: str):
        time.sleep(int(sleep))

    def __assertion_response_value(self, response_data, ass_response_value):
        _dict = {}
        method = None
        try:
            if ass_response_value:
                for i in ass_response_value:
                    value = self.get_json_path_value(response_data, i['actual'])
                    _dict = {'actual': str(value)}
                    if i.get('expect'):
                        try:
                            _dict['expect'] = str(eval(i.get('expect')))
                        except (NameError, SyntaxError):
                            _dict['expect'] = i.get('expect')
                    method = i.get('method')
                    getattr(self, method)(**_dict)
        except AssertionError as error:
            log.api.debug(error)
            self.ass_result.append(AssResultModel(type=method, expect=_dict.get('expect'), actual=_dict.get('actual')))
            raise ApiError(*ERROR_MSG_0005)
        except ToolsError as error:
            raise ApiError(error.code, error.msg)

    def __assertion_sql(self, sql_list: list[dict]):
        _dict = {'actual': None}
        method = None
        try:
            if self.mysql_connect:
                for sql in sql_list:
                    actual = self.mysql_connect.condition_execute(self.replace(sql.get('actual')))
                    if not actual:
                        raise ApiError(*ERROR_MSG_0041)
                    if isinstance(actual, list):
                        _dict = {'actual': str(list(actual[0].values())[0])}
                    if sql.get('expect'):
                        _dict['expect'] = sql.get('expect')
                    method = sql.get('method')
                    getattr(self, method)(**_dict)
        except AssertionError as error:
            log.api.debug(error)
            self.ass_result.append(AssResultModel(type=method, expect=_dict.get('expect'), actual=_dict.get('actual')))
            raise ApiError(*ERROR_MSG_0006)

    def __assertion_response_whole(self, actual: dict, expect: dict):
        try:
            self.ass_response_whole(actual, expect)
        except AssertionError as error:
            log.api.debug(error)
            self.ass_result.append(AssResultModel(type='全匹配断言',
                                                  expect=json.dumps(expect, ensure_ascii=False),
                                                  actual=json.dumps(expect, ensure_ascii=False)))
            raise ApiError(*ERROR_MSG_0004, value=(expect, actual))
