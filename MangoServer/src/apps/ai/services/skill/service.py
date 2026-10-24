# -*- coding: utf-8 -*-
from copy import copy
from dataclasses import dataclass

from src.apps.ai.enums import AiSkillTypeEnum
from src.apps.ai.models import AiSkill
from src.apps.ai.services.core import SkillService
from src.common.prompts.functional_test import DEFAULT_FUNCTIONAL_CASE_SKILL_CONTENT

DEFAULT_FUNCTIONAL_CASE_SKILL_CODE = "functional_case_design_default"
DEFAULT_FUNCTIONAL_CASE_SKILL_NAME = "功能测试用例设计默认技能"


@dataclass
class DefaultSkill:
    id: int | None
    name: str
    description: str
    content: str
    skill_type: int
    status: int


class AgentSkillService:
    @staticmethod
    def get_skill(skill_id: int | None = None, code: str | None = None) -> AiSkill | None:
        return SkillService.published_skill(code, skill_id=skill_id)

    @staticmethod
    def get_default_functional_case_skill() -> AiSkill | DefaultSkill:
        skill = (
                AiSkill.objects.filter(status=1, skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value,
                                       name=DEFAULT_FUNCTIONAL_CASE_SKILL_NAME).order_by("-id").first()
                or AiSkill.objects.filter(status=1, skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value,
                                          description__contains=DEFAULT_FUNCTIONAL_CASE_SKILL_CODE).order_by(
            "-id").first()
                or AiSkill.objects.filter(status=1, skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value,
                                          content__contains=DEFAULT_FUNCTIONAL_CASE_SKILL_CODE).order_by("-id").first()
        )
        if skill:
            return skill
        return DefaultSkill(
            id=None,
            name=DEFAULT_FUNCTIONAL_CASE_SKILL_NAME,
            description="平台内置默认技能，不依赖数据库预置记录",
            content=DEFAULT_FUNCTIONAL_CASE_SKILL_CONTENT,
            skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value,
            status=1,
        )

    @classmethod
    def resolve_functional_case_skill(cls, skill_id: int | None = None) -> AiSkill | DefaultSkill:
        skill = cls.get_skill(skill_id=skill_id) if skill_id else None
        if skill and skill.skill_type == AiSkillTypeEnum.FUNCTIONAL_TEST.value:
            return skill
        return cls.get_default_functional_case_skill()

    @staticmethod
    def materialize_task_skill(task, skill: AiSkill | DefaultSkill | None):
        skill_version = getattr(task, "skill_version", None)
        if not skill or not skill_version or getattr(skill, "id", None) != skill_version.skill_id:
            return skill
        versioned_skill = copy(skill)
        versioned_skill.content = skill_version.content
        return versioned_skill

    @staticmethod
    def build_skill_prompt(skill: AiSkill | DefaultSkill | None) -> str:
        if not skill:
            return ""
        return f"技能规则：\n{skill.content}"

    @staticmethod
    def skill_snapshot(skill: AiSkill | DefaultSkill | None) -> dict:
        if not skill:
            return {}
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "content": skill.content,
            "is_builtin": bool(getattr(skill, "is_builtin", False)),
            "skill_type": getattr(skill, "skill_type", None),
            "status": skill.status,
        }
