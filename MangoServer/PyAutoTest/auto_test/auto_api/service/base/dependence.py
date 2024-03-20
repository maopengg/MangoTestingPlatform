# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json
import logging
import time
from collections import Counter

from PyAutoTest.auto_test.auto_api.service.base.common_parameters import CommonParameters
from PyAutoTest.exceptions.api_exception import *
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.assertion.public_assertion import PublicAssertion
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0004, ERROR_MSG_0005, ERROR_MSG_0007, ERROR_MSG_0010, \
    ERROR_MSG_0006

log = logging.getLogger('api')


class ApiDataHandle(CommonParameters, PublicAssertion):

    def request_data(self, request_data_model: RequestDataModel):
        """
        检查请求信息中是否存在变量进行替换
        @param request_data_model:
        @return:
        """
        for key, value in request_data_model:
            if value is not None and key != 'file':
                value = self.replace(value)
                if key == 'headers' and isinstance(value, str):
                    value = self.replace(self.loads(value))
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
        return request_data_model

    def front_sql(self, case_detailed):
        """
        前置sql
        @param case_detailed:
        @return:
        """
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
        if case_detailed.ass_response_value:
            self.__assertion_response_value(response_data, self.replace(case_detailed.ass_response_value))
        if case_detailed.ass_sql:
            self.__assertion_sql(self.replace(case_detailed.ass_sql))
        if case_detailed.ass_response_whole:
            self.__assertion_response_whole(response_data, self.replace(case_detailed.ass_response_whole))

    def posterior(self, response: ResponseDataModel, case_detailed):
        """
        后置处理
        @param response:
        @param case_detailed:
        @return:
        """
        if case_detailed.posterior_response:
            self.__posterior_response(response.response_json, self.replace(case_detailed.posterior_response))
        if case_detailed.posterior_sql:
            self.__posterior_sql(self.replace(case_detailed.posterior_sql))
        if case_detailed.posterior_sleep:
            self.__posterior_sleep(self.replace(case_detailed.posterior_sleep))

    def dump_data(self, case_detailed):
        """
        后置数据清除
        @param case_detailed:
        @return:
        """
        if self.mysql_connect:
            for sql in case_detailed.dump_data:
                if sql.strip().lower().startswith('select'):
                    raise DumpDataError(*ERROR_MSG_0010)
                res = self.mysql_connect.condition_execute(self.replace(sql))
                if isinstance(res, int):
                    log.info(f'删除成功的条数：{res}')

    def __posterior_sql(self, sql_list: list[dict]):
        """
        后置sql
        @param sql_list:
        @return:
        """
        if self.mysql_connect:
            for sql_obj in sql_list:
                res = self.mysql_connect.condition_execute(sql_obj.get('key'))
                if isinstance(res, list):
                    for res_dict in res:
                        for key, value in res_dict.items():
                            self.set_cache(sql_obj.get('value'), value)
                            log.info(f'{sql_obj.get("value")}sql写入的数据：{self.get_cache(sql_obj.get("value"))}')

    def __posterior_response(self, response_text: dict, posterior_response: list[dict]):
        """
        后置响应
        @return:
        """
        for i in posterior_response:
            value = self.get_json_path_value(response_text, i['key'])
            self.set_cache(i['value'], value)

    @classmethod
    def __posterior_sleep(cls, sleep: str):
        time.sleep(int(sleep))

    def __assertion_response_value(self, response_data, ass_response_value):
        """
        响应jsonpath断言
        @param response_data:
        @param ass_response_value:  list[dict]
        @return:
        """
        try:
            if ass_response_value:
                for i in ass_response_value:
                    value = self.get_json_path_value(response_data, i['value'])
                    _dict = {'value': str(value)}
                    if i.get('expect'):
                        _dict['expect'] = i.get('expect')
                    getattr(self, i['method'])(**_dict)
        except AssertionError:
            raise ResponseValueAssError(*ERROR_MSG_0005)

    def __assertion_sql(self, sql_list: list[dict]):
        """
        sql断言
        @param sql_list:
        @return:
        """
        try:
            if self.mysql_connect:
                for sql in sql_list:
                    value = self.mysql_connect.condition_execute(self.replace(sql.get('value')))
                    if isinstance(value, list):
                        _dict = {'value': str(list(value[0].values())[0])}
                    else:
                        _dict = {'value': None}
                    if sql.get('expect'):
                        _dict['expect'] = sql.get('expect')
                    getattr(self, sql['method'])(**_dict)
        except AssertionError:
            raise SqlAssError(*ERROR_MSG_0006)

    @classmethod
    def __assertion_response_whole(cls, actual, expect):
        """
        响应全匹配断言
        @param actual:
        @param expect:
        @return:
        """
        try:
            assert Counter(actual) == Counter(json.loads(expect))
        except AssertionError:
            raise ResponseWholeAssError(*ERROR_MSG_0004)
