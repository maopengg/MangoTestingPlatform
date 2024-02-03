# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.service.ui_test_run import UiTestRun
from PyAutoTest.auto_test.auto_ui.models import UiElement
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.enums.tools_enum import ClientNameEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.data_processor import DataProcessor
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData
from PyAutoTest.tools.view_utils.response_msg import *


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
        books = self.model.objects.filter(page_id=request.query_params.get('page_id')).order_by('id')
        return ResponseData.success(RESPONSE_MSG_0077, self.get_serializer_class()(instance=books, many=True).data,
                                    len(books))


class UiElementViews(ViewSet):
    model = UiElement
    serializer_class = UiElementSerializers

    @action(methods=['POST'], detail=False)
    def test_element(self, request: Request):
        """
        获取所有的页面名称
        """
        try:
            UiTestRun(request.user.get('id'), request.data.get("testing_environment")).element(request.data)
        except MangoServerError as error:
            return ResponseData.fail((error.code, error.msg))
        return ResponseData.success(RESPONSE_MSG_0081, value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['get'], detail=False)
    def get_ele_name(self, request: Request):
        """
        获取
        :param request:
        :return:
        """
        res = UiElement.objects.filter(page=request.query_params.get('id')).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0080, data)

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
        return ResponseData.success(RESPONSE_MSG_0079, )

    @action(methods=['get'], detail=False)
    def is_element_locator(self, request: Request):
        obj = self.model.objects.get(id=request.query_params.get('element_id'))
        res_bool = DataProcessor.is_extract(obj.loc)
        if res_bool:
            return ResponseData.success(RESPONSE_MSG_0078, '1')
        else:
            return ResponseData.success(RESPONSE_MSG_0078, '0')
