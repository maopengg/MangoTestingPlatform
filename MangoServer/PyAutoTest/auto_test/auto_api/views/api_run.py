# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-16 20:48
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.data_producer.run_api_send import RunApiSend
from PyAutoTest.settings import DRIVER, SERVER


class RunApiCase(ViewSet):

    @action(methods=['get'], detail=False)
    def api_run(self, request: Request):
        case_json, res = RunApiSend(request.query_params.get("username"),
                                    request.query_params.get("test_obj")).request_data(
            request.query_params.get("case_id"), True)
        return Response({
            'code': 200,
            'msg': f'{DRIVER}已收到全部用例，正在执行中...',
            'data': case_json
        }) if res else Response({
            'code': 300,
            'msg': f'执行失败，请确保{DRIVER}已连接{SERVER}',
            'data': case_json
        })

    @action(methods=['get'], detail=False)
    def api_batch_run(self, request: Request):
        case_json, res = RunApiSend(request.query_params.get("username"),
                                    request.query_params.get("test_obj")).batch_requests_data(
            eval(request.query_params.get("case_list")))
        return Response({
            'code': 200,
            'msg': f'{DRIVER}已收到全部用例，正在执行中...',
            'data': case_json
        }) if res else Response({
            'code': 300,
            'msg': f'执行失败，请确保{DRIVER}已连接{SERVER}',
            'data': case_json
        })

    @action(methods=['get'], detail=False)
    def api_group_run(self, request: Request):
        case_json, res = RunApiSend(request.query_params.get("username"),
                                    request.query_params.get("test_obj")).group_case_data(
            request.query_params.get("group_name"),
            eval(request.query_params.get("case_list")))
        return Response({
            'code': 200,
            'msg': f'{DRIVER}已收到全部用例，正在执行中...',
            'data': case_json
        }) if res else Response({
            'code': 300,
            'msg': f'执行失败，请确保{DRIVER}已连接{SERVER}',
            'data': case_json
        })
