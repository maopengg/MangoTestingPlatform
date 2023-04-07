# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 22:10
# @Author : 毛鹏
import json

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_ui.case_run.case_data import CaseData


class RunUiCase(ViewSet):

    @action(methods=['get'], detail=False)
    def ui_run(self, request):
        """
        执行用例接口
        @param request:
        @return:
        """
        environment = request.GET.get("environment")
        case_id = int(request.GET.get("case_id"))
        case_data_list = CaseData(request.user).processing_use_cases(case_id, environment)
        case_data_ = ''
        for i in case_data_list:
            case_data_ += i['case_name']
            case_data_ += '，'
        server = ChatConsumer()
        f = server.active_send(
            code=200,
            func='web_case_run',
            user=int(request.user.get('username')),
            msg=f'接收到用例：{case_data_}准备开始执行自动化任务！',
            data=case_data_list,
            end='client_obj'
        )
        if f is True:
            return Response({
                'code': 200,
                'msg': '测试客户端已收到用例，正在执行中...',
                'data': case_data_list
            })
        else:
            return Response({
                'code': 300,
                'msg': '执行失败，请确保执行端已连接服务器',
                'data': case_data_list
            })

    @action(methods=['get'], detail=False)
    def ui_batch_run(self, request):
        """
        多线程批量运行接口用例
        @param request:
        @return:
        """
        # team = request.GET.get("team")
        environment = request.GET.get("environment")
        case_id = int(request.GET.get("case_id"))
        # case_name = UiCase.objects.get(id=case_id).name
        # r = UiCaseRun()
        # # try:
        # r.main(team, environment, case_id)
        data = CaseData(case_id).data_ui_case(environment)
        return Response({
            'code': 200,
            'msg': '测试客户端已收到用例，正在执行中...',
            'data': data
        })
