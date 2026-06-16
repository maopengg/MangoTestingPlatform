# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.request import Request

from src.apps.functional_test.models import ManualTestSuite
from src.apps.functional_test.service.suite import ManualTestSuiteService
from src.apps.system.views.product_module import ProductModuleSerializers
from src.apps.system.views.project_product import ProjectProductSerializersC
from src.apps.user.views.user import UserSerializers
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class ManualTestSuiteSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    last_sync_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestSuite
        fields = "__all__"

    def validate(self, attrs):
        if not (attrs.get("owner") or getattr(self.instance, "owner_id", None)):
            raise serializers.ValidationError({"owner": "测试负责人不能为空"})
        return attrs


class ManualTestSuiteSerializerC(ManualTestSuiteSerializer):
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    owner = UserSerializers(read_only=True)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("project_product", "project_product__project", "module", "owner")


class ManualTestSuiteCRUD(ModelCRUD):
    model = ManualTestSuite
    queryset = ManualTestSuite.objects.all()
    serializer_class = ManualTestSuiteSerializerC
    serializer = ManualTestSuiteSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["owner", "sync_status"]

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            ManualTestSuiteService.refresh_stats(serializer.data["id"])
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
