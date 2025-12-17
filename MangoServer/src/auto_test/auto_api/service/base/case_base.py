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
            for i in parametrize.get('parametrize'):
                key = i.get('key', None)
                value = i.get('value', None)
                if not key or not value:
                    raise ApiError(*ERROR_MSG_0032)
                value = self.test_setup.test_data.replace(i.get('value'))
                log.api.debug(f'用例参数化->key:{i.get("key")}，value：{value}')
                self.test_setup.test_data.set_cache(i.get('key'), value)

    def __front_custom(self, front_custom):
        for custom in front_custom:
            key = custom.get('key', None)
            value = custom.get('value', None)
            if not key or not value:
                raise ApiError(*ERROR_MSG_0029)
            log.api.debug(f'前置自定义->key:{key}，value:{value}')
            self.test_setup.test_data.set_cache(key, value)

    def __front_sql(self, front_sql):
        if self.test_setup.mysql_connect:
            for i in front_sql:
                key = self.test_setup.test_data.replace(i.get('key'))
                value = self.test_setup.test_data.replace(i.get('value'))
                if not value:
                    raise ApiError(*ERROR_MSG_0036)
                res: list[dict] = self.test_setup.mysql_connect.condition_execute(value)
                log.api.debug(f'用例前置sql-1->key:{key}，value:{value}，查询结果：{res}')
                if isinstance(res, list) and len(res) > 0 and key:
                    self.test_setup.test_data.set_sql_cache(key, res[0])
                if not res and key:
                    log.api.debug(f'用例前置sql-2->key:{key}，res:{res}')
                    raise ApiError(*ERROR_MSG_0034, value=(value,))

    def __front_headers(self):
        if self.api_case.front_headers:
            for i in ApiHeaders.objects.filter(id__in=self.api_case.front_headers):
                self.case_headers[i.key] = i.value
        log.api.debug(f'前置自定义->用例headers:{self.case_headers}')

    def __posterior_sql(self, posterior_sql):
        if self.test_setup.mysql_connect:
            for sql in posterior_sql:
                key = self.test_setup.test_data.replace(self.test_setup.test_data.replace(sql.get('key')))
                sql = self.test_setup.test_data.replace(self.test_setup.test_data.replace(sql.get('value')))
                if not sql:
                    raise ApiError(*ERROR_MSG_0026)
                res = self.test_setup.mysql_connect.condition_execute(sql)
                log.api.debug(f'用例后置sql->key:{key},sql:{sql},查询结果：{res}')
                if key is not None or key != '' and len(res) > 0:
                    self.test_setup.test_data.set_sql_cache(key, res[0])
