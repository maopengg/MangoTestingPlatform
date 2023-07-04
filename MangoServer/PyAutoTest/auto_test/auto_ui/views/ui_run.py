# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 22:10
# @Author : 毛鹏

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.data_producer.run_api import RunApi
from PyAutoTest.settings import DRIVER, SERVER


class RunUiCase(ViewSet):

    @action(methods=['get'], detail=False)
    def ui_run(self, request: Request):
        """
        执行一条用例
        @param request:
        @return:
        """
        case_json, res = RunApi(request.user.get("username")).case_run_batch(case_list=int(request.GET.get("case_id")),
                                                                             te=request.GET.get("te"),
                                                                             user_id=request.user.get("id"))
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

    # @action(methods=['get'], detail=False)
    # def ui_batch_run(self, request):
    #     """
    #     批量执行多条用例
    #     @param request:
    #     @return:
    #     """
    #     environment = request.GET.get("environment")
    #     case_json, res = self.run_data.case_run_batch(case_list=int(request.GET.get("case_id")),
    #                                                   environment=environment,
    #                                                   username=int(request.user.get('username')))
    #     if res:
    #         return Response({
    #             'code': 200,
    #             'msg': f'{DRIVER}已收到全部用例，正在执行中...',
    #             'data': case_json
    #         })
    #     else:
    #         return Response({
    #             'code': 300,
    #             'msg': f'执行失败，请确保{DRIVER}已连接服务器',
    #             'data': case_json
    #         })

    @action(methods=['get'], detail=False)
    def ui_run_group(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        case_json, res = RunApi(request.user.get("username")).group_batch(group_id_list=int(request.GET.get("group_id")))
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

    @action(methods=['get'], detail=False)
    def ui_run_group_batch(self, request: Request):
        """
        批量执行多个用例组
        @param request:
        @return:
        """
        group_id_list = eval(request.GET.get("group_id"))
        case_json, res = RunApi(request.user.get("username")).group_batch(group_id_list=group_id_list)
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
