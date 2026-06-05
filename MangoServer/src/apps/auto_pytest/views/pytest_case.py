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

from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_pytest.service.base.update_file import UpdateFile
from src.apps.auto_pytest.service.test_case.test_case import TestCase
from src.apps.auto_pytest.views.pytest_product import PytestProductSerializersC
from src.apps.auto_system.views.product_module import ProductModuleSerializers
from src.apps.auto_user.views.user import UserSerializers
from src.common.enums.pytest_enum import FileStatusEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class PytestCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'


class PytestCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = PytestProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'case_people',
        )
        return queryset


class PytestCaseCRUD(ModelCRUD):
    model = PytestCase
    queryset = PytestCase.objects.all()
    serializer_class = PytestCaseSerializersC
    serializer = PytestCaseSerializers


class PytestCaseViews(ViewSet):
    model = PytestCase
    serializer_class = PytestCaseSerializers

    @action(methods=['post'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        project_id = request.data.get('project_id')
        if not project_id:
            return ResponseData.error(RESPONSE_MSG_0079)

        product = PytestProduct.objects.filter(id=project_id).first()
        if not product:
            return ResponseData.error(RESPONSE_MSG_0080)

        file_path_list = list(self.model.objects.all().values_list('file_path', flat=True))
        _file_path_list = []
        created_count = 0
        for project in UpdateFile(product.test_dir).find_test_files(product.file_name):
            # 分离 .py 文件和 .feature 文件
            py_files = [f for f in project.auto_test if f.path.endswith('.py')]
            feature_files = {os.path.basename(f.name).replace('.feature', ''): f.path for f in project.auto_test if f.path.endswith('.feature')}
            
            for file in py_files:
                _file_path_list.append(file.path)
                # 检查是否有同名的 .feature 文件
                # file.name 可能包含目录路径，如 'alert\test_alert_bdd.py'
                # 需要提取纯文件名进行匹配
                pure_file_name = os.path.basename(file.name)
                file_name_without_ext = pure_file_name.replace('.py', '')
                feature_file_path = feature_files.get(file_name_without_ext)

                pytest_act, created = self.model.objects.get_or_create(
                    file_path=file.path,
                    defaults={
                        'name': file.name,
                        'file_name': file.name,
                        'file_status': FileStatusEnum.UNBOUND.value,
                        'file_update_time': file.time.replace(tzinfo=None),
                        'project_product': product,
                        'feature_file_path': feature_file_path,
                    }
                )
                if created:
                    created_count += 1
                else:
                    pytest_act.file_update_time = file.time.replace(tzinfo=None)
                    # 更新 feature_file_path（可能新增或删除了 feature 文件）
                    pytest_act.feature_file_path = feature_file_path
                    pytest_act.save()
        deleted_files = set(file_path_list) - set(_file_path_list)
        if deleted_files:
            self.model.objects.filter(file_path__in=deleted_files).update(
                file_status=FileStatusEnum.DELETED.value,
            )
        return ResponseData.success(RESPONSE_MSG_0078, value=(created_count,))

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_read(self, request: Request):
        case = self.model.objects.get(id=request.query_params.get('id'))
        file_type = request.query_params.get('file_type', 'py')
        
        if file_type == 'feature' and case.feature_file_path:
            file_path = case.feature_file_path
        else:
            file_path = case.file_path
            
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        return ResponseData.success(RESPONSE_MSG_0084, data=file_content)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_write(self, request: Request):
        case = self.model.objects.get(id=request.data.get('id'))
        file_type = request.data.get('file_type', 'py')
        file_content = request.data.get('file_content')
        
        if file_type == 'feature' and case.feature_file_path:
            file_path = case.feature_file_path
        else:
            file_path = case.file_path
            
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(file_content)
        return ResponseData.success(RESPONSE_MSG_0085)

    @action(methods=['GET'], detail=False)
    @error_response('pytest')
    def pytest_test_case(self, request: Request):

        report_data = TestCase(request.user.get('username')) \
            .test_case(request.query_params.get('id'), int(request.query_params.get("test_env")))
        return ResponseData.success(RESPONSE_MSG_0086, data=report_data)
