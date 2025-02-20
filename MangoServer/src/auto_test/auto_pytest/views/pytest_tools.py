# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_pytest.models import PytestTools
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_pytest.views.pytest_module import PytestProjectModuleSerializersC
from src.auto_test.auto_pytest.views.pytest_project import PytestProjectSerializersC
from src.enums.pytest_enum import PytestFileTypeEnum, FileStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestToolsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestTools
        fields = '__all__'


class PytestToolsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    pytest_project = PytestProjectSerializersC(read_only=True)
    module = PytestProjectModuleSerializersC(read_only=True)

    class Meta:
        model = PytestTools
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
        )
        return queryset


class PytestToolsCRUD(ModelCRUD):
    model = PytestTools
    queryset = PytestTools.objects.all()
    serializer_class = PytestToolsSerializersC
    serializer = PytestToolsSerializers


class PytestToolsViews(ViewSet):
    model = PytestTools
    serializer_class = PytestToolsSerializers

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        for project in UpdateFile(PytestFileTypeEnum.TOOLS).find_test_files():
            for file in project.file:
                for act in file.tools:
                    pytest_act, created = self.model.objects.get_or_create(
                        file_path=act.path,
                        defaults={
                            'name': act.name,
                            'file_name': act.name,
                            'file_status': FileStatusEnum.UNBOUND.value,
                            'file_update_time': act.time.replace(tzinfo=None),

                        }
                    )
                    if not created:
                        pytest_act.file_update_time = act.time.replace(tzinfo=None)
                        pytest_act.save()
        return ResponseData.success(RESPONSE_MSG_0074)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_read(self, request: Request):
        file_path = self.model.objects.get(id=request.query_params.get('id')).file_path
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        return ResponseData.success(RESPONSE_MSG_0084, data=file_content)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_write(self, request: Request):
        file_path = self.model.objects.get(id=request.data.get('id')).file_path
        file_content = request.data.get('file_content')
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(file_content)
        return ResponseData.success(RESPONSE_MSG_0085)
