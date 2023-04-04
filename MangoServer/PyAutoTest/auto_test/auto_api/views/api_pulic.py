# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.api_tools.enum import PublicRelyType, End
from PyAutoTest.auto_test.auto_api.models import ApiPublic
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.utils.view_utils.view_tools import enum_list


class ApiPublicSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiPublic
        fields = '__all__'


class ApiPublicCRUD(ModelCRUD):
    model = ApiPublic
    queryset = ApiPublic.objects.all()
    serializer_class = ApiPublicSerializers


class ApiPublicViews(ViewSet):
    # @staticmethod
    # def get_header(request):
    #     data = []
    #     for i in ApiPublic.objects.filter(type=2, end=request.GET.get('end')):
    #         da = {}
    #         for key, value in vars(i).items():
    #             if key != "_state":
    #                 da[key] = value
    #         data.append(da)
    #     return JsonResponse({
    #         'code': 200,
    #         'msg': '查询成功~',
    #         'data': data
    #     })

    @action(methods=['get'], detail=False)
    def get_public_type(self, request):
        """
        获取公共类型
        :param request:
        :return:
        """
        return Response({
            'code': 200,
            'msg': '获取类型成功',
            'data': enum_list(PublicRelyType)
        })

    @action(methods=['get'], detail=False)
    def get_end_type(self, request):
        """
        获取客户端类型
        :param request:
        :return:
        """
        return Response({
            'code': 200,
            'msg': '获取类型成功',
            'data': enum_list(End)
        })
