# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_ui.models import Page, PageElement
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PageSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Page
        fields = '__all__'  # 全部进行序列化
        # fields = ['project']  # 选中部分进行序列化
        # exclude = ['name']  # 除了这个字段，其他全序列化


class PageSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    module = ProductModuleSerializers(read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = Page
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'module',
            'project_product')
        return queryset


class PageCRUD(ModelCRUD):
    model = Page
    queryset = Page.objects.all()
    serializer_class = PageSerializersC
    # post专用序列化器
    serializer = PageSerializers


class PageViews(ViewSet):
    model = Page
    serializer_class = PageSerializers

    @action(methods=['GET'], detail=False)
    @error_response('ui')
    def page_name(self, request: Request):
        """
        根据项目获取页面id和名称
        """
        module_id = request.query_params.get('module_id')
        if module_id:
            res = Page.objects.filter(module=module_id).values_list('id', 'name')
        else:
            res = Page.objects.all().values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        if data:
            return ResponseData.success(RESPONSE_MSG_0052, data)

        else:
            return ResponseData.fail(RESPONSE_MSG_0053)

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def page_copy(self, request: Request):
        from src.auto_test.auto_ui.views.ui_element import PageElementSerializers
        page_id = request.data.get('page_id')
        page_obj = Page.objects.get(id=page_id)
        page_obj = model_to_dict(page_obj)
        page_id = page_obj['id']
        page_obj['name'] = '(副本)' + page_obj['name']
        del page_obj['id']
        serializer = self.serializer_class(data=page_obj)
        if serializer.is_valid():
            serializer.save()
            page_elements = PageElement.objects.filter(page=page_id)
            for i in page_elements:
                page_element = model_to_dict(i)
                del page_element['id']
                page_element['page'] = serializer.data['id']
                page_element_serializer = PageElementSerializers(data=page_element)
                if page_element_serializer.is_valid():
                    page_element_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0054, serializer.errors)
            return ResponseData.success(RESPONSE_MSG_0055, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0054, serializer.errors)
