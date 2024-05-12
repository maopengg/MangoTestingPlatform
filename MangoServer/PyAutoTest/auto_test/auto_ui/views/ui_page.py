# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPage, UiElement
from PyAutoTest.auto_test.auto_user.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_user.views.project_product import ProjectProductSerializersC
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class UiPageSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiPage
        fields = '__all__'  # 全部进行序列化
        # fields = ['project']  # 选中部分进行序列化
        # exclude = ['name']  # 除了这个字段，其他全序列化


class UiPageSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    module = ProductModuleSerializers(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = UiPage
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'module',
            'project_product')
        return queryset


class UiPageCRUD(ModelCRUD):
    model = UiPage
    queryset = UiPage.objects.all()
    serializer_class = UiPageSerializersC
    # post专用序列化器
    serializer = UiPageSerializers


class UiPageViews(ViewSet):
    model = UiPage
    serializer_class = UiPageSerializers

    @action(methods=['GET'], detail=False)
    def page_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        module = request.query_params.get('module')
        if module:
            res = UiPage.objects.filter(module=module).values_list('id', 'name')
        else:
            res = UiPage.objects.all().values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        if data:
            return ResponseData.success(RESPONSE_MSG_0052, data)

        else:
            return ResponseData.fail(RESPONSE_MSG_0053)

    @action(methods=['post'], detail=False)
    def page_copy(self, request: Request):
        from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementSerializers
        page_id = request.data.get('page_id')
        page_obj = UiPage.objects.get(id=page_id)
        page_obj = model_to_dict(page_obj)
        page_id = page_obj['id']
        page_obj['name'] = '(副本)' + page_obj['name']
        del page_obj['id']
        serializer = self.serializer_class(data=page_obj)
        if serializer.is_valid():
            serializer.save()
            page_elements = UiElement.objects.filter(page=page_id)
            for i in page_elements:
                page_element = model_to_dict(i)
                del page_element['id']
                page_element['page'] = serializer.data['id']
                page_element_serializer = UiElementSerializers(data=page_element)
                if page_element_serializer.is_valid():
                    page_element_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0054, serializer.errors)
            return ResponseData.success(RESPONSE_MSG_0055, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0054, serializer.errors)
