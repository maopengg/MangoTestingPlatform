# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:57
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCase, ApiHeaders
from src.auto_test.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.exceptions import *


class CaseBase:
    """ 测试用例前后置 """

    def __init__(self, test_setup: APIBaseTestSetup, api_case: ApiCase):
        self.test_setup = test_setup
        self.api_case = api_case
        self.case_headers = {}

    def case_front_main(self):
        if self.api_case.front_custom:
            self.__front_custom(self.api_case.front_custom)
        if self.api_case.front_sql:
            self.__front_sql(self.api_case.front_sql)
        if self.api_case.front_headers:
            self.__front_headers()

    def case_posterior_main(self, ):
        if self.api_case.posterior_sql:
            self.__posterior_sql(self.api_case.posterior_sql)

    def case_parametrize(self, parametrize: dict):
        if parametrize:
            for i in parametrize:
                key = i.get('key', None)
                value = i.get('value', None)
                if key is None or value is None:
                    raise ApiError(*ERROR_MSG_0032)
                value = self.test_setup.test_data.replace(i.get('value'))
                log.api.debug(f'用例参数化->key:{i.get("key")}，value：{value}')
                self.test_setup.test_data.set_cache(i.get('key'), value)

    def __front_custom(self, front_custom: list):
        for custom in front_custom:
            log.api.debug(f'前置自定义->key:{custom.get("key")}，value:{custom.get("value")}')
            self.test_setup.test_data.set_cache(custom.get('key'), custom.get('value'))

    def __front_sql(self, front_sql: list[dict]):
        if self.test_setup.mysql_connect:
            for i in front_sql:
                sql = self.test_setup.test_data.replace(i.get('sql'))
                result_list: list[dict] = self.test_setup.mysql_connect.condition_execute(sql)
                log.api.debug(f'前置自定义->key:{sql}，value:{result_list}')
                if isinstance(result_list, list) and len(result_list) > 0:
                    self.test_setup.test_data.set_sql_cache(i.get('key_list'), result_list[0])
                    if not result_list:
                        raise ApiError(*ERROR_MSG_0034, value=(sql,))

    def __front_headers(self):
        if self.api_case.front_headers:
            for i in ApiHeaders.objects.filter(id__in=self.api_case.front_headers):
                self.case_headers[i.key] = i.value
        log.api.debug(f'前置自定义->用例headers:{self.case_headers}')

    def __posterior_sql(self, posterior_sql: list[dict]):
        for sql in posterior_sql:
            sql = self.test_setup.test_data.replace(self.test_setup.test_data.replace(sql.get('sql')))
            log.api.debug(f'后置sql->sql:{sql}')
            self.test_setup.mysql_connect.condition_execute(sql)
