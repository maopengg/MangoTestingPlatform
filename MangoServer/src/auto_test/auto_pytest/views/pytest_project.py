# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_pytest.models import PytestProject, PytestCase
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_pytest.service.base.version_control import GitRepo
from src.enums.pytest_enum import PytestFileTypeEnum, FileStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestProjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestProject
        fields = '__all__'


class PytestProjectSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestProject
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
        )
        return queryset


class PytestProjectCRUD(ModelCRUD):
    model = PytestProject
    queryset = PytestProject.objects.all()
    serializer_class = PytestProjectSerializersC
    serializer = PytestProjectSerializers


class PytestProjectViews(ViewSet):
    model = PytestProject
    serializer_class = PytestProjectSerializers

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        repo = GitRepo()
        repo.pull_repo()
        for project in UpdateFile(PytestFileTypeEnum.TEST_CASE).find_test_files(True):
            if not self.model.objects.filter(name=project.project_name).exists():
                self.model.objects.create(
                    name=project.project_name,
                    init_file=project.init_file_path,
                )
        return ResponseData.success(RESPONSE_MSG_0078)
