# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.models import AiSkill
from src.apps.ai.service.core import SkillService
from src.apps.user.views.user import UserSerializers
from src.common.enums.ai_enum import AiSkillStatusEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class AiSkillSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = AiSkill
        fields = "__all__"

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related("user")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["user"] = UserSerializers(instance=instance.user).data if instance.user_id else None
        return data


class AiSkillCRUD(ModelCRUD):
    model = AiSkill
    queryset = AiSkill.objects.all()
    serializer_class = AiSkillSerializer
    serializer = AiSkillSerializer

    @error_response("system")
    def post(self, request: Request):
        data = dict(request.data)
        data.setdefault("status", AiSkillStatusEnum.PUBLISHED.value)
        data.setdefault("user", request.user.get("id") if isinstance(request.user, dict) else None)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        return super().put(dict(request.data))


class AiSkillViews(ViewSet):
    model = AiSkill
    serializer_class = AiSkillSerializer

    @action(methods=["post"], detail=False)
    @error_response("system")
    def publish(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=SkillService.publish(skill)).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def disable(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.status = AiSkillStatusEnum.DISABLED.value
        skill.save(update_fields=["status", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def archive(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.status = AiSkillStatusEnum.ARCHIVED.value
        skill.save(update_fields=["status", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)
