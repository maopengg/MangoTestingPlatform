# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.request import Request

from src.apps.functional_test.models import FunctionalTestContextResource
from src.common.enums.manual_test_enum import FunctionalTestContextUrlTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class FunctionalTestContextResourceSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = FunctionalTestContextResource
        fields = "__all__"


class FunctionalTestContextResourceSerializerC(FunctionalTestContextResourceSerializer):
    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("suite", "file", "create_user", "update_user")


class FunctionalTestContextResourceCRUD(ModelCRUD):
    model = FunctionalTestContextResource
    queryset = FunctionalTestContextResource.objects.all()
    serializer_class = FunctionalTestContextResourceSerializerC
    serializer = FunctionalTestContextResourceSerializer
    not_matching_str = ModelCRUD.not_matching_str + ["suite", "context_key", "content_type", "url_type", "parse_status", "enabled"]

    @staticmethod
    def validate_url_type(data):
        if data.get("url_type") == FunctionalTestContextUrlTypeEnum.FEISHU.value:
            return ResponseData.fail(RESPONSE_MSG_0183)
        return None

    @error_response("system")
    def post(self, request: Request):
        error = self.validate_url_type(request.data)
        if error:
            return error
        data = dict(request.data)
        data["create_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        error = self.validate_url_type(request.data)
        if error:
            return error
        data = dict(request.data)
        data["update_user"] = request.user.get("id") if isinstance(request.user, dict) else None
        serializer = self.serializer(self.model.objects.get(id=request.data.get("id")), data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0082, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
