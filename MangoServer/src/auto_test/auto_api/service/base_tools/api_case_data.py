# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:57
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCase
from src.auto_test.auto_api.service.base_tools.case_base import CaseBase
from src.exceptions import *


class ApiCaseData(CaseBase):

    def init_case_front(self, api_case):
        self.__front_custom(api_case)
        self.__front_sql(api_case)
        self.__front_headers(api_case)

    def init_case_posterior(self, api_case):
        self.__posterior_sql(api_case)

    def __front_custom(self, api_case: ApiCase):
        for custom in api_case.front_custom:
            self.set_cache(custom.get('key'), custom.get('value'))

    def __front_sql(self, api_case: ApiCase):
        for i in api_case.front_sql:
            if self.mysql_connect:
                sql = self.replace(i.get('sql'))
                result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                if isinstance(result_list, list):
                    for result in result_list:
                        try:
                            key_list = eval(i.get('key_list'))
                            for value, key in zip(result, key_list):
                                self.set_cache(key, result.get(value))
                        except SyntaxError:
                            raise ApiError(*ERROR_MSG_0036)
                        except NameError:
                            raise ApiError(*ERROR_MSG_0036)
                    if not result_list:
                        raise ApiError(*ERROR_MSG_0034, value=(sql,))

    def __front_headers(self, api_case: ApiCase):
        if api_case.front_headers:
            self.headers = api_case.front_headers

    def __posterior_sql(self, api_case: ApiCase):
        for sql in api_case.posterior_sql:
            self.mysql_connect.condition_execute(self.replace(sql.get('sql')))
