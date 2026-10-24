# -*- coding: utf-8 -*-
from urllib.parse import quote

from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.ai.api.serializers.skill import AiSkillSerializer
from src.apps.ai.enums import AiSkillStatusEnum
from src.apps.ai.models import AiSkill
from src.apps.ai.services.core import SkillService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0082,
)


class AiSkillCRUD(ModelCRUD):
    model = AiSkill
    queryset = AiSkill.objects.all()
    serializer_class = AiSkillSerializer
    serializer = AiSkillSerializer
    page_permission_key = 'ai.skill'

    @error_response("system")
    def post(self, request: Request):
        data = self.with_update_user(request, request.data.copy())
        skill_file = request.FILES.get("skill_file")
        if skill_file:
            # 上传 Skill 文件时，直接把文件文本写入现有 content 字段。
            data["content"] = skill_file.read().decode("utf-8")
            data.setdefault("name", skill_file.name.rsplit(".", 1)[0])
        data.setdefault("status", AiSkillStatusEnum.PUBLISHED.value)
        data.setdefault("user", request.user.get("id") if isinstance(request.user, dict) else None)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @error_response("system")
    def put(self, request: Request):
        return super().put(request)


class AiSkillViews(ViewSet):
    model = AiSkill
    serializer_class = AiSkillSerializer
    action_permission_map = {
        'download': 'ai.skill:download',
        'publish': 'ai.skill:status',
        'disable': 'ai.skill:status',
        'archive': 'ai.skill:status',
    }

    @action(methods=["get"], detail=False)
    @error_response("system")
    def download(self, request: Request):
        skill = AiSkill.objects.get(id=request.query_params.get("id"))
        filename = f"{skill.name or skill.id}.md"
        response = HttpResponse(skill.content or "", content_type="text/markdown; charset=utf-8")
        # 兼容中文文件名，避免浏览器下载时文件名乱码。
        response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

    @action(methods=["post"], detail=False)
    @error_response("system")
    def publish(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        skill = SkillService.publish(skill)
        skill.save(update_fields=["update_user", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def disable(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.status = AiSkillStatusEnum.DISABLED.value
        skill.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        skill.save(update_fields=["status", "update_user", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def archive(self, request: Request):
        skill = AiSkill.objects.get(id=request.data.get("id"))
        skill.status = AiSkillStatusEnum.ARCHIVED.value
        skill.update_user_id = request.user.get("id") if isinstance(request.user, dict) else None
        skill.save(update_fields=["status", "update_user", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, AiSkillSerializer(instance=skill).data)
