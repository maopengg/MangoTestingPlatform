# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-16 20:48
# @Author : 毛鹏
import json

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.case_data_processing.run_api_send import RunApiSend
from PyAutoTest.settings import DRIVER, SERVER


class RunApiCase(ViewSet):

    @action(methods=['get'], detail=False)
    def api_run_(self, request: Request):
        case_list = eval(request.query_params.get('case_id_list'))
        test_obj = request.query_params.get('test_obj')
        case_json, res = RunApiSend.group_case_list(case_list, test_obj, request.user.get('username'))
        print(json.dumps(case_json))
        if res:
            return Response({
                'code': 200,
                'msg': f'{DRIVER}已收到全部用例，正在执行中...',
                'data': case_json
            })
        else:
            return Response({
                'code': 300,
                'msg': f'执行失败，请确保{DRIVER}已连接{SERVER}',
                'data': case_json
            })

    # def api_run(self, request):
    #     """
    #     执行用例接口
    #     """
    #     project = request.GET.get('project')
    #     environment = request.GET.get('environment')
    #     case_id = request.GET.get('id')
    #     r = ApiCaseRun(project, environment)
    #     case, response = r.case_main(case_id)
    #     data = {
    #         'case_id': case.id,
    #         'case_name': case.name,
    #         'url': response.url,
    #         'method': [x.name for x in Method if x.value == case.method][0],
    #         'header': json.dumps(Response.header),
    #         'response_time': Response.response_time,
    #         'code': response.status_code,
    #         'body_type': [x.name if x.value == case.body_type else 'null' for x in OpeType][0],
    #         'environment': [x.name for x in EnvironmentEnum if x.value == int(environment)][0],
    #         'assertion': '成功',
    #         'body': json.dumps(Response.body),
    #         'response': response.json()}
    #     return JsonResponse({
    #         'code': 200,
    #         'data': data,
    #         'msg': '测试成功'
    #     })
