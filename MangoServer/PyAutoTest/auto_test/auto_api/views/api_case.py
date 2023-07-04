# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.service.automatic_parsing_interface import ApiParameter
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('api')


class ApiCaseSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiCase
        fields = '__all__'


class ApiCaseCRUD(ModelCRUD):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializers


class ApiCaseViews(ViewSet):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializers

    @action(methods=['get'], detail=False)
    def api_synchronous_interface(self, request):
        """
        同步接口
        @param request:
        @return:
        """
        host = request.GET.get('host')
        team_id = request.GET.get('team_id')
        case_list = ApiParameter(host, team_id).get_stage_api()
        res = []
        for i in case_list:
            serializer = self.serializer_class(data=i)
            if serializer.is_valid():
                serializer.save()
                res.append(True)
            else:
                logger.error(f"错误信息：{str(serializer.errors)}"
                             f"错误数据：{i}")
                res.append(False)
        if False in res:
            return Response({
                'code': 200,
                'msg': '接口同步包含部分失败',
                'data': None
            })
        return Response({
            'code': 200,
            'msg': '接口同步成功',
            'data': None
        })
