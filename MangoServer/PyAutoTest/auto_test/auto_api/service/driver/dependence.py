# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json
import logging
from collections import Counter

import time

from PyAutoTest.auto_test.auto_api.service.driver.common_parameters import CommonParameters
from PyAutoTest.exceptions.api_exception import *
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.assertion.public_assertion import PublicAssertion

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
                    value = self.loads(value)
                setattr(request_data_model, key, value)
            elif key == 'file':
                file = []
                if request_data_model.file:
                    for i in request_data_model.file:
                        i: list[dict] = i
                        for k, v in i.items():
                            file_name = self.identify_parentheses(v)[0].replace('(', '').replace(')', '')
                            path = self.replace(v)
                            file.append((k, (file_name, open(f'{str(path)}', 'rb'))))
                request_data_model.file = file
        return request_data_model

    def front_sql(self, case_detailed):
        """
        前置sql
        @param case_detailed:
        @return:
        """
        self.__sql_(self.replace(case_detailed.front_sql), '前置')

    def assertion(self, response: ResponseDataModel, case_detailed) -> None:
        if response.response_json:
            response_data = response.response_json
        else:
            try:
                response_data = eval(response.response_text)
            except SyntaxError:
                raise ResponseSyntaxError('响应数据语法错误，返回的数据非json格式，请检查服务是否正常！')
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
        if self.is_db:
            for sql in case_detailed.dump_data:
                if sql.strip().lower().startswith('select'):
                    raise DumpDataError('数据清除不支持查询数据操作')
                res = self.mysql_obj.execute(self.replace(sql))
                if isinstance(res, int):
                    log.info(f'删除成功的条数：{res}')

    def __posterior_sql(self, sql_list: list[dict]):
        """
        后置sql--需要测试
        @param sql_list:
        @return:
        """
        for obj in sql_list:
            for sql, value_key in obj.items():
                res = self.mysql_obj.execute(sql)
                if isinstance(res, list):
                    for res_dict in res:
                        for key, value in res_dict.items():
                            self.set_cache(value_key, value)
                            log.info(f'{value_key}sql写入的数据：{self.get_cache(value_key)}')

    def __posterior_response(self, response_text: dict, posterior_response: list[dict]):
        """
        后置响应
        @return:
        """
        for i in posterior_response:
            value = self.get_json_path_value(response_text, i['key'])
            self.set_cache(i['value'], value)

    def __posterior_sleep(self, sleep: str):
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
            raise ResponseValueAssError('响应jsonpath断言失败')

    def __assertion_sql(self, sql: list):
        """
        sql断言--还需要完善
        @param sql:
        @return:
        """
        try:
            if self.is_db:
                res = self.mysql_obj.execute(sql)
                log.info(res)
        except AssertionError:
            raise SqlAssError('sql断言失败')

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
            raise ResponseWholeAssError('全匹配断言失败')

    def __sql_(self, sql_list: list, _str: str):
        if self.is_db:
            for sql in sql_list:
                res = self.mysql_obj.execute(sql)
                if isinstance(res, list):
                    for i in res:
                        for key, value in i.items():
                            self.set_cache(key, value)
                            log.info(f'{_str}sql写入的数据：{self.get_cache(key)}')