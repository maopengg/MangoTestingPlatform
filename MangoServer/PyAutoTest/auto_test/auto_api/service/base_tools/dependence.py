# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json
import logging
from collections import Counter

import time
from retrying import retry

from PyAutoTest.auto_test.auto_api.service.base_tools.common_base import CommonBase
from PyAutoTest.exceptions.api_exception import *
from PyAutoTest.exceptions.error_msg import *
from PyAutoTest.exceptions.tools_exception import CacheIsEmptyError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.assertion.public_assertion import PublicAssertion
from PyAutoTest.tools.base_request.request_tool import BaseRequest

log = logging.getLogger('api')


class CaseMethod(CommonBase, PublicAssertion):
    ass_result = []

    def send_request(self, request_data_model: RequestDataModel, is_debug: bool = False) -> ResponseDataModel:
        base_request = BaseRequest()
        base_request.request(self.request_data_clean(request_data_model, is_debug))
        return base_request.request_result_data()

    def request_data_clean(self, request_data_model: RequestDataModel, is_debug: bool):
        for key, value in request_data_model:
            if key == 'headers' and isinstance(value, str):
                if is_debug:
                    try:
                        value = self.replace(value)
                    except CacheIsEmptyError:
                        pass
                else:
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
                new_dict = self.replace(self.headers, False)
                if new_dict and isinstance(new_dict, str):
                    new_dict = self.loads(new_dict) if new_dict else new_dict
                request_data_model.headers = self.__merge_dicts(request_data_model.headers, new_dict)

        return request_data_model

    def front_sql(self, case_detailed):
        if self.mysql_connect:
            for sql in case_detailed.front_sql:
                res = self.mysql_connect.condition_execute(sql)
                if isinstance(res, list):
                    for i in res:
                        for key, value in i.items():
                            self.set_cache(key, value)
                            log.info(f'前置sql写入的数据：{self.get_cache(key)}')

    def assertion(self, response: ResponseDataModel, case_detailed) -> None:
        if response.response_json:
            response_data = response.response_json
        else:
            try:
                response_data = eval(response.response_text)
            except SyntaxError:
                raise ResponseSyntaxError(*ERROR_MSG_0007)
            except ValueError:
                raise ResponseSyntaxError(*ERROR_MSG_0039)
        self.ass_result = []
        if case_detailed.ass_response_value:
            self.__assertion_response_value(response_data, self.replace(case_detailed.ass_response_value))
        if case_detailed.ass_sql:
            self.__assertion_sql(self.replace(case_detailed.ass_sql))
        if case_detailed.ass_response_whole:
            self.__assertion_response_whole(response_data, self.replace(case_detailed.ass_response_whole))

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
                            log.info(f'{sql_obj.get("value")}sql写入的数据：{self.get_cache(sql_obj.get("value"))}')

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
            log.warning(error)
            self.ass_result.append({'断言类型': method, '预期值': _dict.get('expect'), '实际值': _dict.get('actual')})
            raise ResponseValueAssError(*ERROR_MSG_0005)

    @retry(stop_max_attempt_number=5, wait_fixed=1000)
    def __assertion_sql(self, sql_list: list[dict]):
        _dict = {'actual': None}
        method = None
        try:
            if self.mysql_connect:
                for sql in sql_list:
                    actual = self.mysql_connect.condition_execute(self.replace(sql.get('actual')))
                    if not actual:
                        raise SqlResultIsNoneError(*ERROR_MSG_0041)
                    if isinstance(actual, list):
                        _dict = {'actual': str(list(actual[0].values())[0])}
                    if sql.get('expect'):
                        _dict['expect'] = sql.get('expect')
                    method = sql.get('method')
                    getattr(self, method)(**_dict)
        except AssertionError as error:
            log.warning(error)
            self.ass_result.append({'断言类型': method, '预期值': _dict.get('expect'), '实际值': _dict.get('actual')})
            raise SqlAssError(*ERROR_MSG_0006)

    def __assertion_response_whole(self, actual, expect):
        try:
            assert Counter(actual) == Counter(json.loads(expect))
        except AssertionError as error:
            log.warning(error)
            self.ass_result.append({'断言类型': '全匹配断言', '预期值': expect, '实际值': '查看响应结果和预期'})
            raise ResponseWholeAssError(*ERROR_MSG_0004, value=(expect, actual))

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
