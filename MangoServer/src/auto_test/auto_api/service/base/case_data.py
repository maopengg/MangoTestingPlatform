# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 20:57
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCase, ApiHeaders
from src.auto_test.auto_api.service.base.api_info import ApiInfoBase
from src.exceptions import *


class ApiCaseBase(ApiInfoBase):

    def case_front_main(self, api_case: ApiCase):
        if api_case.front_custom:
            self.__front_custom(api_case.front_custom)  # type: ignore
        if api_case.front_sql:
            self.__front_sql(api_case.front_sql)  # type: ignore
        if api_case.front_headers:
            self.__front_headers(api_case)

    def case_posterior_main(self, api_case: ApiCase):
        if api_case.posterior_sql:
            self.__posterior_sql(api_case.posterior_sql)  # type: ignore

    def __front_custom(self, front_custom):
        for custom in front_custom:
            self.set_cache(custom.get('key'), custom.get('value'))

    def __front_sql(self, front_sql: list[dict]):
        if self.mysql_connect:
            for i in front_sql:
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
            case_details_header = {}
            for i in ApiHeaders.objects.filter(id__in=api_case.front_headers):
                case_details_header[i.key] = i.value
            self.case_headers = case_details_header
        else:
            self.case_headers = self.init_headers()

    def __posterior_sql(self, posterior_sql: list[dict]):
        for sql in posterior_sql:
            self.mysql_connect.condition_execute(self.replace(sql.get('sql')))

    def case_parametrize(self, parametrize: dict):
        if parametrize:
            for i in parametrize:
                self.set_cache(i.get('key'), self.replace(i.get('value')))
