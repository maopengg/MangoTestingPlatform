# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiElement
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.enums.ui_enum import ElementExpEnum
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.view_tools import enum_list


class UiElementSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiElement
        fields = '__all__'


class UiElementSerializersC(serializers.ModelSerializer):
    page = UiPageSerializers(read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiElement
        fields = '__all__'  # 全部进行序列化


class UiElementCRUD(ModelCRUD):
    model = UiElement
    queryset = UiElement.objects.all()
    serializer_class = UiElementSerializersC
    serializer = UiElementSerializers

    def get(self, request):
        try:
            books = self.model.objects.filter(page_id=request.query_params.get('page_id')).order_by('id')
            return ResponseData.success('获取数据成功', self.get_serializer_class()(instance=books, many=True).data,
                                        len(books))
        except:
            return ResponseData.fail('您查询的数据不存在')


class UiElementViews(ViewSet):
    model = UiElement
    serializer_class = UiElementSerializers

    @action(methods=['get'], detail=False)
    def get_ele_name(self, request: Request):
        """
        获取
        :param request:
        :return:
        """
        res = UiElement.objects.filter(page=request.query_params.get('id')).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)

    @action(methods=['get'], detail=False)
    def get_exp_type(self, request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取数据成功', enum_list(ElementExpEnum))

    @action(methods=['put'], detail=False)
    def put_is_iframe(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.is_iframe = request.data.get('is_iframe')
        obj.save()
        return ResponseData.success('修改状态成功', )
