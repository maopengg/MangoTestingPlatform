# -*- coding: utf-8 -*-
from dataclasses import dataclass

from src.apps.ai.models import AiSkill
from src.apps.ai.service.core import SkillService
from src.common.enums.ai_enum import AiSkillTypeEnum


DEFAULT_FUNCTIONAL_CASE_SKILL_CODE = "functional_case_design_default"
DEFAULT_FUNCTIONAL_CASE_SKILL_NAME = "功能测试用例设计默认技能"
DEFAULT_FUNCTIONAL_CASE_SKILL_CONTENT = """# 功能测试用例设计默认技能

## 目标
你需要作为业务测试专家，把需求资料、原始用例资料和用户补充要求，设计成测试平台可落库的功能测试用例。

## 固定流程
1. 先理解需求：抽取业务目标、用户角色、主流程、分支流程、状态流转、验收点和关键数据。
2. 再识别已有覆盖：从原始用例中提取已覆盖的功能点、异常点、边界点、权限点、数据点和流程点。
3. 再做差异分析：明确哪些验收点缺失，哪些正常/异常/边界/权限/数据/流程场景不足。
4. 再生成用例：围绕差异结果补齐用例，同时保留原始用例中有效的 case。
5. 最后校验：去重、补齐必填字段、映射平台枚举、保证编号稳定。

## 平台字段规则
- case_no：统一按 FT-{四位序号} 生成，例如 FT-0001、FT-0002；不要使用模块缩写，不要沿用原始文档中的 TC-* 编号。
- title：简洁描述验证目标，不写泛化标题。
- precondition：写清前置用户、权限、数据、配置或状态。
- test_point：写清本用例验证点。
- test_data：写清关键入参、数据库状态或构造数据。
- test_types：多选，必须从平台枚举中选择；默认包含手工测试，适合接口自动化时增加 API 自动化。
- priority、scenario_layer、scenario_type、scenario_tags 必须使用平台数字枚举。

## 覆盖要求
- 必须覆盖主成功路径、重要异常、边界输入、权限隔离、数据状态流转和关键业务流程。
- 不允许只生成示例，不允许只生成前 10 条。
- 如果原始用例已有大量 case，输出数量应接近真实覆盖需要；如合并或舍弃，必须在 warnings 说明。
"""


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
            AiSkill.objects.filter(status=1, skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value, name=DEFAULT_FUNCTIONAL_CASE_SKILL_NAME).order_by("-id").first()
            or AiSkill.objects.filter(status=1, skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value, description__contains=DEFAULT_FUNCTIONAL_CASE_SKILL_CODE).order_by("-id").first()
            or AiSkill.objects.filter(status=1, skill_type=AiSkillTypeEnum.FUNCTIONAL_TEST.value, content__contains=DEFAULT_FUNCTIONAL_CASE_SKILL_CODE).order_by("-id").first()
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
