# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-16 20:48
# @Author : 毛鹏
import json

from django.http.response import JsonResponse
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.api_tools.data_model import Response
from PyAutoTest.auto_test.auto_api.api_tools.enum import OpeType, Method
from PyAutoTest.auto_test.auto_api.case_run.case_run import ApiCaseRun
from PyAutoTest.enum_class.ui_enum import EnvironmentEnum


class RunApiCase(ViewSet):
    @staticmethod
    def api_run(request):
        """
        执行用例接口
        """
        project = request.GET.get('project')
        environment = request.GET.get('environment')
        case_id = request.GET.get('id')
        r = ApiCaseRun(project, environment)
        case, response = r.case_main(case_id)
        data = {
            'case_id': case.id,
            'case_name': case.name,
            'url': response.url,
            'method': [x.name for x in Method if x.value == case.method][0],
            'header': json.dumps(Response.header),
            'response_time': Response.response_time,
            'code': response.status_code,
            'body_type': [x.name if x.value == case.body_type else 'null' for x in OpeType][0],
            'environment': [x.name for x in EnvironmentEnum if x.value == int(environment)][0],
            'assertion': '成功',
            'body': json.dumps(Response.body),
            'response': response.json()}
        return JsonResponse({
            'code': 200,
            'data': data,
            'msg': '测试成功~'
        })

    @staticmethod
    def api_batch_run(request):
        """
        多线程批量运行接口用例
        @param request:
        @return:
        """
        pass
