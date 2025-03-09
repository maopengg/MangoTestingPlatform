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

from src.auto_test.auto_pytest.models import PytestTestFile
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_pytest.service.base.version_control import GitRepo
from src.auto_test.auto_pytest.views.pytest_product import PytestProductSerializersC
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.pytest_enum import PytestFileTypeEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestTestFileSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestTestFile
        fields = '__all__'


class PytestTestFileSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = PytestProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = PytestTestFile
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
        )
        return queryset


class PytestTestFileCRUD(ModelCRUD):
    model = PytestTestFile
    queryset = PytestTestFile.objects.all()
    serializer_class = PytestTestFileSerializersC
    serializer = PytestTestFileSerializers


class PytestTestFileViews(ViewSet):
    model = PytestTestFile
    serializer_class = PytestTestFileSerializers

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        for project in UpdateFile(PytestFileTypeEnum.UPLOAD, GitRepo().local_warehouse_path).find_test_files():
            for file in project.auto_test:
                pytest_act, created = self.model.objects.get_or_create(
                    file_path=file.path,
                    defaults={
                        'name': os.path.basename(file.name),
                        'file_update_time': file.time.replace(tzinfo=None),

                    }
                )
                if not created:
                    pytest_act.file_update_time = file.time.replace(tzinfo=None)
                    pytest_act.save()
        return ResponseData.success(RESPONSE_MSG_0078)
