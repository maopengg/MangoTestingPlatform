# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 解决接口的依赖关系
# @Time   : 2022-11-10 21:24
# @Author : 毛鹏
import json
import os
import traceback

import requests
import time

from mangotools.assertion import MangoAssertion
from mangotools.exceptions import MangoToolsError
from src.auto_test.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.enums.tools_enum import StatusEnum
from src.exceptions import *
from src.models.api_model import ResponseModel, RequestModel, AssResultModel
from src.tools import project_dir
from ...models import ApiCaseDetailedParameter, ApiHeaders


class CaseParameter:
    """ 测试用例详情的前后置+断言+缓存 """

    def __init__(self, api_base_test_setup: APIBaseTestSetup, parameter: ApiCaseDetailedParameter):
        self.test_setup = api_base_test_setup
        self.parameter = parameter
        self.ass_result: list[AssResultModel] = []

        self.test_data = api_base_test_setup.test_data
        self.test_object = api_base_test_setup.test_object
        self.mysql_connect = api_base_test_setup.mysql_connect

    def headers(self, parameter: ApiCaseDetailedParameter) -> dict:
        case_details_header = {}
        if parameter.headers:
            for i in ApiHeaders.objects.filter(id__in=parameter.headers):
                case_details_header[i.key] = i.value
        return case_details_header

    def front_main(self, request: RequestModel) -> RequestModel:
        if self.parameter.front_sql:
            self.__front_sql(self.parameter.front_sql)
        if self.parameter.front_func:
            request = self.__front_func(self.parameter.front_func, request)
        return request

    def ass_main(self, response: ResponseModel, ) -> tuple[list[AssResultModel], int, str | None]:
        try:
            if self.parameter.ass_jsonpath:
                ass_jsonpath = self.test_setup.test_data.replace(self.parameter.ass_jsonpath)
                self.__ass_jsonpath(response.json, ass_jsonpath)
            # if self.parameter.ass_sql:
            #     ass_sql = self.test_setup.test_data.replace(self.parameter.ass_sql)
            #     self.__ass_sql(ass_sql)
            if self.parameter.ass_general:
                ass_general = self.test_setup.test_data.replace(self.parameter.ass_general)
                self.__ass_general(ass_general)
            if self.parameter.ass_json_all:
                ass_json_all = self.test_setup.test_data.replace(self.parameter.ass_json_all)
                self.__ass_json_all(response.json, ass_json_all)
            if self.parameter.ass_text_all:
                self.__ass_test_all(response.text, self.test_setup.test_data.replace(self.parameter.ass_text_all))
        except (ToolsError, ApiError, MangoToolsError) as error:
            return self.ass_result, StatusEnum.FAIL.value, error.msg
        except Exception as e:
            log.api.error(f'API断言发生未知错误，管理员请检查：{e}，{traceback.print_exc()}')
            return self.ass_result, StatusEnum.FAIL.value, f'API断言发生未知错误，管理员请检查：{e}'
        return self.ass_result, StatusEnum.SUCCESS.value, None

    def posterior_main(self, response: ResponseModel) -> ResponseModel:
        if self.parameter.posterior_response:
            self.__posterior_response(
                response.json,
                self.test_setup.test_data.replace(self.parameter.posterior_response)
            )
        if self.parameter.posterior_sql:
            self.__posterior_sql(self.test_setup.test_data.replace(self.parameter.posterior_sql))
        if self.parameter.posterior_sleep:
            time.sleep(int(self.parameter.posterior_sleep))
        if self.parameter.posterior_func:
            response = self.__posterior_func(self.parameter.posterior_func, response)
        if self.parameter.posterior_file:
            self.__posterior_file(self.parameter.posterior_file)
        return response

    def __posterior_func(self, posterior_func: str, response: ResponseModel) -> RequestModel:
        try:
            log.api.debug(f'用例详情后置-3->函数：{posterior_func}')
            return self.test_setup.analytic_func(posterior_func)(self, response)
        except (KeyError, MangoToolsError) as error:
            log.api.debug(f"数据报错，函数：{posterior_func}, request:{response.model_dump_json()}, error：{error}")
            raise ApiError(*ERROR_MSG_0013)

    def __posterior_sql(self, sql_list: list[dict]):
        if self.test_setup.mysql_connect:
            for sql_obj in sql_list:
                sql = self.test_setup.test_data.replace(sql_obj.get('key'))
                res = self.test_setup.mysql_connect.condition_execute(sql)
                log.api.debug(f'用例详情后置-2->key：{sql_obj.get("value")}，sql：{sql}，结果：{res}')
                if isinstance(res, list) and len(res) > 0:
                    log.api.debug(f'前置sql写入的数据：{sql_obj.get("value")},sql: {res[0]}')
                    self.test_setup.test_data.set_sql_cache(sql_obj.get('value'), res[0])

    def __posterior_response(self, response_text: dict, posterior_response: list[dict]):
        for i in posterior_response:
            key: str = i.get('key')
            if key and key.startswith('$.'):
                key = self.test_setup.test_data.get_json_path_value(response_text, i.get('key'))
            value = self.test_setup.test_data.get_json_path_value(response_text, i.get('value'))
            log.api.debug(f'用例详情后置-1->key：{i["value"]}，value：{value}')
            self.test_setup.test_data.set_cache(key, value)

    def __posterior_file(self, posterior_file: list[dict]):
        for i in posterior_file:
            url_path = i.get('value')
            if not url_path:
                continue
            try:
                filename = os.path.basename(url_path.split("?")[0])
                local_file_path = os.path.join(project_dir.download(), filename)
                response = requests.get(url_path, stream=True, timeout=30, proxies={'http': None, 'https': None})
                response.raise_for_status()
                with open(local_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                self.test_setup.test_data.set_cache(i.get('key'), local_file_path)
            except Exception as e:
                log.api.error(f'下载文件异常：{traceback.format_exc()}')
                raise ApiError(*ERROR_MSG_0016, value=(e,))

    def __ass_jsonpath(self, response_data, ass_jsonpath):
        if ass_jsonpath:
            for i in ass_jsonpath:
                ass_dict = {
                    'expect': self.test_setup.test_data.replace(i.get('expect')),
                    'actual': str(self.test_setup.test_data.get_json_path_value(response_data, i['actual'])),
                    'method': i.get('method')
                }
                mango_assertion = MangoAssertion()
                self.__ass_(mango_assertion, ass_dict, ERROR_MSG_0005)

    def __ass_general(self, general: list[dict]):
        for i in general:
            ass_dict = {
                'method': i.get('value').get('value'),
                'actual': '',
                'expect': ''
            }
            for p in i.get('value', {}).get('parameter', []):
                ass_dict[p.get('f')] = p.get('v')
            mango_assertion = MangoAssertion(self.mysql_connect)
            self.__ass_(mango_assertion, ass_dict, ERROR_MSG_0007)

    def __ass_sql(self, sql_list: list[dict]):
        if self.test_setup.mysql_connect:
            for sql in sql_list:
                ass_dict = {
                    'expect': self.test_setup.test_data.replace(sql.get('expect')),
                    'actual': self.test_setup.test_data.replace(sql.get('actual')),
                    'method': sql.get('method')
                }
                mango_assertion = MangoAssertion()
                self.__ass_(mango_assertion, ass_dict, ERROR_MSG_0007)

    def __ass_json_all(self, actual: dict, expect: dict):
        log.api.debug(f'用例详情断言-3->实际：{actual}，预期：{expect}')
        ass_result = AssResultModel(
            method='JSON一致性断言',
            actual=None,
            expect=json.dumps(expect, ensure_ascii=False)
        )
        try:
            assert actual is not None, f'实际={actual}, 预期={ass_result.expect}'
            ass_result.actual = json.dumps(actual, ensure_ascii=False)
            ass_result.ass_msg = MangoAssertion().p_in_dict(actual, expect)
            self.ass_result.append(ass_result)
        except AssertionError as error:
            ass_result.ass_msg = str(error.args[0]) if error.args else ''
            self.ass_result.append(ass_result)
            raise ApiError(300, ass_result.ass_msg)

    def __ass_test_all(self, actual: str, expect: str):
        log.api.debug(f'用例详情断言-4->实际：{actual}，预期：{expect}')
        ass_result = AssResultModel(
            method='文本一致性断言',
            actual=actual,
            expect=expect,
            ass_msg=f'实际={actual}, 预期={expect}'
        )
        self.ass_result.append(ass_result)
        try:
            assert actual.strip() == expect.strip(), f'实际={actual}, 预期={expect}'
        except AssertionError as error:
            ass_result.ass_msg = str(error.args[0]) if error.args else ''
            self.ass_result.append(ass_result)
            raise ApiError(300, ass_result.ass_msg)

    def __ass_(self, mango_assertion, ass_dict: dict, _error_msg: tuple):
        ass_result = AssResultModel(
            method=getattr(mango_assertion, ass_dict['method']).__doc__,
            actual=ass_dict['actual'],
            expect=ass_dict['expect'],
        )
        if ass_dict['expect'] == '':
            ass_dict['expect'] = None
        log.api.info(f'用例详情断言-1->{ass_dict}')
        try:
            ass_result.ass_msg = mango_assertion.ass(**ass_dict)
            self.ass_result.append(ass_result)
        except AssertionError as error:
            ass_result.ass_msg = str(error.args[0]) if error.args else ''
            self.ass_result.append(ass_result)
            raise ApiError(300, ass_result.ass_msg)


    def __front_sql(self, front_sql):
        if self.test_setup.mysql_connect and front_sql:
            for sql in front_sql:
                sql = self.test_setup.test_data.replace(sql)
                res = self.test_setup.mysql_connect.condition_execute(sql)
                log.api.debug(f'用例详情前置-1->sql：{sql}，查询结果：{res}')

    def __front_func(self, front_func: str, request: RequestModel) -> RequestModel:
        try:
            log.api.debug(f'用例详情前置-2->{front_func}')
            return self.test_setup.analytic_func(front_func)(self, request)
        except (KeyError, MangoToolsError) as error:
            log.api.error(f"数据报错，函数：{front_func}, request:{request.model_dump_json()}, error：{error}")
            raise ApiError(*ERROR_MSG_0010)
