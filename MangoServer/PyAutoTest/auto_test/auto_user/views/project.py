# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 项目表
# @Time   : 2023-03-03 12:21
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_user.service.files_crud import FilesCRUD
from PyAutoTest.enums.system_enum import EnvironmentEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *
from ..models import Project, ProjectProduct
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

    def post(self, request: Request):
        serializer = self.serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            FilesCRUD(serializer.data.get('id')).add_project()
            return ResponseData.success(RESPONSE_MSG_0022, serializer.data)
        else:
            log.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{str(serializer.errors)}')
            return ResponseData.fail(RESPONSE_MSG_0023, serializer.errors)

    def delete(self, request: Request):
        if '[' in request.query_params.get('id'):
            for i in eval(request.query_params.get('id')):
                self.model.objects.get(pk=i).delete()
                FilesCRUD(i).delete_project()
        else:
            # 一条删
            self.model.objects.get(id=request.query_params.get('id')).delete()
            self.asynchronous_callback(request)
            FilesCRUD(request.query_params.get('id')).delete_project()
        return ResponseData.success(RESPONSE_MSG_0024, )


class ProjectViews(ViewSet):
    model = Project
    serializer_class = ProjectSerializers

    @action(methods=['GET'], detail=False)
    def get_all_items(self, request: Request):
        items = Project.objects.filter(status=StatusEnum.SUCCESS.value)
        data = [{'title': i.name, 'key': i.pk} for i in items]
        return ResponseData.success(RESPONSE_MSG_0025, data)

    @action(methods=['GET'], detail=False)
    def project_product_name(self, request: Request):
        book = Project.objects.values_list('id', 'name').all()
        options = []
        for _id, name in book:
            product_list = ProjectProduct.objects.values_list('id', 'name').filter(project=_id)
            options.append({
                'value': _id,
                'label': name,
                'children': [{'value': product_id,
                              'label': product_name,
                              } for product_id, product_name in product_list]
            })
        return ResponseData.success(RESPONSE_MSG_0025, options)

    @action(methods=['GET'], detail=False)
    def project_environment_name(self, request: Request):
        book = Project.objects.values_list('id', 'name').all()
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
            product_id_list = ProjectProduct.objects.values_list('id').filter(project=_id)
            for product_id in product_id_list:
                test_object_list = TestObject.objects \
                    .filter(project_product=product_id)
                for test_object in test_object_list:
                    project_obj['children'].append({'value': test_object.id,
                                                    'label': EnvironmentEnum.get_value(test_object.environment),
                                                    })
            options.append(project_obj)
        return ResponseData.success(RESPONSE_MSG_0095, options)
