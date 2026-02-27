# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
import os

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from src.auto_test.auto_pytest.service.base import git_obj
from src.auto_test.auto_pytest.models import PytestProduct
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_system.models import ProductModule, CacheData
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.system_enum import CacheDataKeyEnum
from src.tools import project_dir
from src.tools.decorator.error_response import error_response
from src.tools.log_collector import log
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestProductSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestProduct
        fields = '__all__'


class PytestProductSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = PytestProduct
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product'
        )
        return queryset


class PytestProductCRUD(ModelCRUD):
    model = PytestProduct
    queryset = PytestProduct.objects.all()
    serializer_class = PytestProductSerializersC
    serializer = PytestProductSerializers


class PytestProductViews(ViewSet):
    model = PytestProduct
    serializer_class = PytestProductSerializers

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        repo = git_obj()
        repo.pull()
        update_file = UpdateFile('').find_test_files(True)
        for project in update_file:
            projects = self.model.objects.filter(file_name=project.project_name)
            if not projects.exists():
                self.model.objects.create(
                    name=project.project_name,
                    file_name=project.project_name,
                    init_file=project.init_file_path,
                )
        return ResponseData.success(RESPONSE_MSG_0078)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_push(self, request: Request):
        repo = git_obj()
        repo.push()
        return ResponseData.success(RESPONSE_MSG_0090)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_read(self, request: Request):
        file_path = self.model.objects.get(id=request.query_params.get('id')).init_file
        with open(os.path.join(project_dir.root_path(), file_path), 'r', encoding='utf-8') as file:
            file_content = file.read()
        return ResponseData.success(RESPONSE_MSG_0084, data=file_content)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_write(self, request: Request):
        file_path = self.model.objects.get(id=request.data.get('id')).init_file
        file_content = request.data.get('file_content')
        with open(os.path.join(project_dir.root_path(), file_path), 'w', encoding='utf-8') as file:
            file.write(file_content)
        return ResponseData.success(RESPONSE_MSG_0085)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_project_name(self, request: Request):
        """
        获取pytest的项目名称
        @param request:
        @return:
        """
        res = self.model.objects \
            .filter(project_product_id=request.query_params.get('project_product_id')) \
            .values_list('id', 'name')
        data_list = []
        for _id, name in res:
            v = ProductModule.objects.values_list('id', 'name').filter(
                project_product=request.query_params.get('project_product_id'))
            data_list.append({
                'value': _id,
                'label': name,
                'children': [{'value': module_id, 'label': module_name} for module_id, module_name in v]
            })
        return ResponseData.success(RESPONSE_MSG_0154, data_list)
