# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-01-16 20:48
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.data_producer.run_api_send import RunApiSend
from PyAutoTest.settings import DRIVER, SERVER
from PyAutoTest.tools.response_data import ResponseData


class RunApiCase(ViewSet):

    @action(methods=['get'], detail=False)
    def api_run(self, request: Request):
        case_json, res = RunApiSend(request.user.get("username"),
                                    request.query_params.get("test_obj")).request_data(
            request.query_params.get("case_id"), True)
        if res:
            return ResponseData.success(f'{DRIVER}已收到全部用例，正在执行中...', case_json.dict())
        return ResponseData.fail(f'执行失败，请确保{DRIVER}已连接{SERVER}', case_json.dict())

    @action(methods=['get'], detail=False)
    def api_batch_run(self, request: Request):
        case_json, res = RunApiSend(request.user.get("username"),
                                    request.query_params.get("test_obj")).batch_requests_data(
            eval(request.query_params.get("case_list")))
        if res:
            return ResponseData.success(f'{DRIVER}已收到全部用例，正在执行中...', case_json)
        return ResponseData.fail(f'执行失败，请确保{DRIVER}已连接{SERVER}', case_json)

    @action(methods=['get'], detail=False)
    def api_group_run(self, request: Request):
        case_json, res = RunApiSend(request.user.get("username"),
                                    request.query_params.get("test_obj")).group_case_data(
            request.query_params.get("group_name"),
            eval(request.query_params.get("case_list")))
        if res:
            return ResponseData.success(f'{DRIVER}已收到全部用例，正在执行中...', case_json.dict())
        return ResponseData.fail(f'执行失败，请确保{DRIVER}已连接{SERVER}', case_json.dict())
