# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.enums.system_enum import EnvironmentEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *
from ..models import Project, ProjectProduct, ProductModule
from ...auto_system.models import TestObject

log = logging.getLogger('user')


class ProjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = Project
        fields = '__all__'  # 全部进行序列化

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset


class ProjectCRUD(ModelCRUD):
    model = Project
    queryset = Project.objects.all()
    serializer_class = ProjectSerializers
    serializer = ProjectSerializers


class ProjectViews(ViewSet):
    model = Project
    serializer_class = ProjectSerializers

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def get_all_items(self, request: Request):
        """
        项目的ID和name，title选项专用
        @param request:
        @return:
        """
        items = Project.objects.filter(status=StatusEnum.SUCCESS.value)
        data = [{'title': i.name, 'key': i.pk} for i in items]
        data.insert(0, {'title': '选择项目', 'key': None})
        return ResponseData.success(RESPONSE_MSG_0025, data)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def project_product_name(self, request: Request):
        """
        项目和产品的选项
        @param request:
        @return:
        """
        book = Project.objects.values_list('id', 'name').filter(status=StatusEnum.SUCCESS.value)
        options = []
        for _id, name in book:
            project = {
                'value': _id,
                'label': name,
                'children': []
            }
            product_list = ProjectProduct.objects.values_list('id', 'name').filter(project=_id)
            for product_id, product_name in product_list:
                v = ProductModule.objects.values_list('id', 'name').filter(project_product=product_id)
                project['children'].append({
                    'value': product_id,
                    'label': product_name,
                    'children': [{'value': module_id, 'label': module_name} for module_id, module_name in v]})
            options.append(project)
        return ResponseData.success(RESPONSE_MSG_0025, options)

    @action(methods=['GET'], detail=False)
    @error_response('user')
    def project_environment_name(self, request: Request):
        """
        项目测试环境选项
        @param request:
        @return:
        """
        book = Project.objects.values_list('id', 'name').filter(status=StatusEnum.SUCCESS.value)
        options = [{
            'value': -1,
            'label': '请选择测试环境',
            'children': []
        }]
        for _id, name in book:
            project_obj = {
                'value': _id,
                'label': name,
                'children': []
            }
            test_object_environment_list = []

            product_id_list = ProjectProduct.objects.values_list('id').filter(project=_id)
            for product_id in product_id_list:
                test_object_list = TestObject.objects \
                    .filter(project_product=product_id)
                for test_object in test_object_list:
                    if test_object.environment not in test_object_environment_list:
                        test_object_environment_list.append(test_object.environment)
                        project_obj['children'].append({'value': test_object.id,
                                                        'label': EnvironmentEnum.get_value(test_object.environment),
                                                        })
            options.append(project_obj)
        return ResponseData.success(RESPONSE_MSG_0095, options)
