# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
import pandas as pd
from django.core.exceptions import FieldError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_ui.models import PageElement
from src.auto_test.auto_ui.service.test_case.test_case import TestCase
from src.auto_test.auto_ui.views.ui_page import PageSerializers
from src.enums.system_enum import ClientNameEnum
from src.enums.ui_enum import ElementExpEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PageElementSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageElement
        fields = '__all__'


class PageElementSerializersC(serializers.ModelSerializer):
    page = PageSerializers(read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageElement
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'page')
        return queryset


class PageElementCRUD(ModelCRUD):
    model = PageElement
    queryset = PageElement.objects.all()
    serializer_class = PageElementSerializersC
    serializer = PageElementSerializers

    @error_response('ui')
    def get(self, request):
        books = self.model.objects.filter(page_id=request.query_params.get('page_id')).order_by('id')
        try:
            books = self.serializer_class.setup_eager_loading(books)
        except FieldError:
            pass
        return ResponseData.success(RESPONSE_MSG_0077,
                                    self.serializer_class(instance=books,
                                                          many=True).data,
                                    books.count())


class PageElementViews(ViewSet):
    model = PageElement
    serializer_class = PageElementSerializers

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def test_element(self, request: Request):
        """
        获取所有的页面名称
        """
        TestCase(
            request.user.get('id'),
            request.user.get('username'),
            request.data.get("test_env"),
            is_send=request.data.get('is_send')
        ).test_element(request.data)
        return ResponseData.success(RESPONSE_MSG_0081, value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def post_upload_element(self, request):
        uploaded_file = request.FILES['file']
        df = pd.read_excel(uploaded_file, keep_default_na=False)
        df['表达式类型'] = df['表达式类型'].map(ElementExpEnum.reversal_obj())
        df = df.rename(columns={
            '元素名称': 'name',
            '类型-1': 'exp',
            '定位-1': 'loc',
            '类型-2': 'exp2',
            '定位-2': 'loc2',
            '类型-3': 'exp3',
            '定位-3': 'loc3',
            '等待时间（秒）': 'sleep',
            '元素下标（1开始）': 'sub',
        })
        for index, row in df.iterrows():
            record = row.to_dict()
            record['page'] = request.data.get("page_id")
            record['is_iframe'] = 0
            record['sleep'] = None if record['sleep'] == '' else record['sleep']
            record['sub'] = None if record['sub'] == '' else record['sub']
            PageElementCRUD.inside_post(record)
        return ResponseData.success(RESPONSE_MSG_0083)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_element_name(self, request: Request):
        """
        获取
        :param request:
        :return:
        """
        res = PageElement.objects.filter(page=request.query_params.get('id')).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0080, data)

    @action(methods=['put'], detail=False)
    @error_response('ui')
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
