# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-30 10:02
# @Author : 毛鹏
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from PyAutoTest.auto_test.auto_api.api_tools.automatic_parsing_interface import ApiParameter


class ApiAutoInterface(ViewSet):

    @action(methods=['get'], detail=False)
    def api_synchronous_interface(self, request):
        # """
        # 同步接口
        # @param request:
        # @return:
        # """
        # host = request.GET.get('host')
        # team_id = request.GET.get('team_id')
        # ApiParameter(host, team_id).get_stage_api()
        # return Response({
        #     'code': 200,
        #     'msg': '接口同步成功！',
        #     'data': None
        # })
        pass
