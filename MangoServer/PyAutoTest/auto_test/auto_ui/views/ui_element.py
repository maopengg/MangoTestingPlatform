# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.data_producer.ui_test_run import UiTestRun
from PyAutoTest.auto_test.auto_ui.models import UiElement
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.settings import DRIVER
from PyAutoTest.tools.data_processor import DataProcessor
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData


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
        return ResponseData.success('获取数据成功', self.get_serializer_class()(instance=books, many=True).data,
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
        except MangoServerError as e:
            return ResponseData.fail(e.msg)
        return ResponseData.success(f'{DRIVER}已收到元素，正在定位中...', )

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

    @action(methods=['get'], detail=False)
    def is_element_locator(self, request: Request):
        obj = self.model.objects.get(id=request.query_params.get('element_id'))
        res_bool = DataProcessor.is_extract(obj.loc)
        if res_bool:
            return ResponseData.success('判断元素中是否包含${}完成', '1')
        else:
            return ResponseData.success('判断元素中是否包含${}完成', '0')
