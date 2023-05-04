# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 22:10
# @Author : 毛鹏

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_ui.case_run.run_api import RunApi
from PyAutoTest.settings import DRIVER
from PyAutoTest.socket_class.actuator_enum.ui_enum import UiEnum


class RunUiCase(ViewSet):
    run_data = RunApi()

    @action(methods=['get'], detail=False)
    def ui_run(self, request):
        """
        执行一条用例
        @param request:
        @return:
        """
        environment = request.GET.get("environment")
        try:
            case_id = int(request.GET.get("case_id"))
        except ValueError:
            case_id = eval(request.GET.get("case_id"))
        case_json = self.run_data.case_run_batch(case_id, environment, request.user)
        response = self.run_case_send(request, case_json, UiEnum.run_debug_case.value)
        return Response(response)

    @action(methods=['get'], detail=False)
    def ui_batch_run(self, request):
        """
        批量执行多条用例
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
        case_json = self.run_data.case_run_batch(case_id, environment, request.user)
        response = self.run_case_send(request, case_json, UiEnum.run_debug_batch_case.value)
        return Response(response)

    @action(methods=['get'], detail=False)
    def ui_run_group(self, request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        case_id = int(request.GET.get("group_id"))
        case_json = self.run_data.group_batch(case_id, request.user)
        response = self.run_case_send(request, case_json, UiEnum.run_group_case.value)
        return Response(response)

    @action(methods=['get'], detail=False)
    def ui_run_group_batch(self, request):
        """
        批量执行多个用例组
        @param request:
        @return:
        """
        group_id_list = eval(request.GET.get("group_id"))
        case_json = self.run_data.group_batch(group_id_list, request.user)
        response = self.run_case_send(request, case_json, UiEnum.run_group_batch_case.value)
        return Response(response)

    @classmethod
    def run_case_send(cls, request, case_json, func_name: str) -> dict:
        """
        发送给第三方工具方法
        @param request: 请求对象
        @param case_json: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """
        server = ChatConsumer()
        f = server.active_send(
            code=200,
            func=func_name,
            user=int(request.user.get('username')),
            msg=f'{DRIVER}：收到用例数据，准备开始执行自动化任务！',
            data=case_json,
            end='client_obj'
        )
        if f is True:
            return {
                'code': 200,
                'msg': f'{DRIVER}已收到用例，正在执行中...',
                'data': case_json
            }
        else:
            return {
                'code': 300,
                'msg': f'执行失败，请确保{DRIVER}已连接服务器',
                'data': case_json
            }
