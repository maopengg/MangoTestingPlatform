# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


class UiCaseSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiCase
        fields = '__all__'


class UiCaseCRUD(ModelCRUD):
    model = UiCase
    queryset = UiCase.objects.all()
    serializer_class = UiCaseSerializers


class UiCaseViews(ViewSet):
    model = UiCase
    serializer_class = UiCaseSerializers

    @action(methods=['put'], detail=False)
    def put_type(self, request):
        ser = []
        data = []
        for i in eval(request.data.get('id')):
            case = self.model.objects.get(pk=i)
            serializer = self.serializer_class(instance=case,
                                               data={'type': request.data.get('type'),
                                                     'name': case.name})
            if serializer.is_valid():
                serializer.save()
            data.append(serializer.data)
        for i in ser:
            if i is True:
                return Response({
                    'code': 300,
                    'msg': '部分数据可能修改失败，请检查设置的用例',
                    'data': data
                })
        return Response({
            'code': 200,
            'msg': f'设置为{request.data.get("name")}成功',
            'data': data
        })
