# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

from PyAutoTest.auto_test.auto_api.api_tools.data_model import Response
from PyAutoTest.auto_test.auto_api.api_tools.data_model import WebRequestsData, Environment
from PyAutoTest.auto_test.auto_api.api_tools.dependence import Dependence
from PyAutoTest.auto_test.auto_api.api_tools.enum import State
from PyAutoTest.auto_test.auto_api.api_tools.request import Request
from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.system_tools.get_project import get_host


class ApiCaseRun:

    def __init__(self, project: str, environment: int):
        # 用例表数据
        self.project = project
        self.end = None
        Environment.environment = int(environment)

    def case_main(self, case_id):
        """
        控制用例的执行顺序，完成所有的用例执行
        :return:
        """
        case_list = Dependence(case_id).rely_case()
        # 小于2就无依赖用例
        if len(case_list) <= 2:
            response, case = self.case_run(case_list[0])

        else:
            for case_id in reversed(case_list):
                response, case = self.case_run(case_id)
        if response.status_code == 200:
            case.state = State.ADOPT.value
            case.save()
        else:
            case.state = State.FAIL.value
            case.save()
        return case, response

    def case_run(self, case_id: int):
        """
        解决用例的依赖关系，并完成执行
        :param case_id: 用例id
        :return: 返回response, case
        """
        case = ApiCase.objects.get(id=case_id)
        rely = Dependence(case_id=case_id, case=case)
        host = self.host(case)
        header = rely.rely_public()
        Response.header = header
        url, body = rely.rely_url_front_body(url=host)
        Response.body = body
        return Request(case).requests(
            url=url,
            header=header,
            body=body
        ), case

    def host(self, case) -> str:
        """
        处理用例的url
        :param case: 用例对象
        :return:
        """
        if self.end is None:
            self.end = case.client
        if case.client != self.end:
            self.end = case.client
            host = get_host(self.project, Environment.environment)
            WebRequestsData.host = host
            return host + case.url
        else:
            host = get_host(self.project, Environment.environment)
            WebRequestsData.host = host
            return host + case.url
