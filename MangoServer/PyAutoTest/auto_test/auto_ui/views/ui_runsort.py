# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import RunSort
from PyAutoTest.auto_test.auto_ui.ui_tools.enum import OpeType, Assertions
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.utils.view_utils.view_tools import enum_list


class RunSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = RunSort
        fields = '__all__'


class RunSortCRUD(ModelCRUD):
    """
        haha
    """
    model = RunSort
    queryset = RunSort.objects.all()
    serializer_class = RunSortSerializers

    def get(self, request):
        books = self.model.objects.filter(case_id=request.GET.get('case_id')).order_by('run_sort')
        data = []
        for i in books:
            data.append(self.serializer_class(i).data)
        return Response({
            "code": 200,
            "msg": "获取数据成功~",
            "data": data
        })


class RunSortView(ViewSet):
    model = RunSort
    serializer_class = RunSortSerializers

    @action(methods=['get'], detail=False)
    def get_ope_type(self, request):
        return Response({
            'code': 200,
            'msg': '获取操作类型成功',
            'data': enum_list(OpeType)
        })

    @action(methods=['get'], detail=False)
    def get_ass_type(self, request):
        return Response({
            'code': 200,
            'msg': '获取断言类型成功',
            'data': enum_list(Assertions)
        })
