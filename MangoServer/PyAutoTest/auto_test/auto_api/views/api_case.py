# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.service.automatic_parsing_interface import ApiParameter
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('api')


class ApiCaseSerializers(serializers.ModelSerializer):
    class Meta:
        model = ApiCase
        fields = '__all__'


class ApiCaseSerializersC(serializers.ModelSerializer):
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'


class ApiCaseCRUD(ModelCRUD):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializersC
    serializer = ApiCaseSerializers


class ApiCaseViews(ViewSet):
    model = ApiCase
    serializer_class = ApiCaseSerializers

    @action(methods=['get'], detail=False)
    def api_synchronous_interface(self, request: Request):
        """
        同步接口
        @param request:
        @return:
        """
        host = request.GET.get('host')
        project_id = request.GET.get('project_id')
        case_list = ApiParameter(host, project_id).get_stage_api()
        res = []
        for i in case_list:
            serializer = self.serializer_class(data=i)
            if serializer.is_valid():
                serializer.save()
                res.append(True)
            else:
                logger.error(f"错误信息：{str(serializer.errors)}"
                             f"错误数据：{i}")
                res.append(False)
        if False in res:
            return ResponseData.fail('接口同步包含部分失败')
        return ResponseData.success('接口同步成功', )
