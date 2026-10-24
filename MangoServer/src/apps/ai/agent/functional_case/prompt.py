# -*- coding: utf-8 -*-
from src.apps.ai.enums.role import AgentRole
from src.apps.ai.services.skill.service import AgentSkillService
from src.common.prompts.functional_test import FUNCTIONAL_CASE_SCHEMA_PROMPT

CASE_SCHEMA_PROMPT = FUNCTIONAL_CASE_SCHEMA_PROMPT


def build_system_prompt(skill, ai_role: str | None) -> str:
    role_key = AgentRole.normalize(ai_role, AgentRole.BUSINESS_TEST_EXPERT)
    role = AgentRole.prompt(role_key, AgentRole.BUSINESS_TEST_EXPERT)
    skill_prompt = AgentSkillService.build_skill_prompt(skill)
    return "\n\n".join([role, FUNCTIONAL_CASE_SCHEMA_PROMPT, skill_prompt]).strip()
