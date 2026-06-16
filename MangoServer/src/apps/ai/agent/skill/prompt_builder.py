# -*- coding: utf-8 -*-
from src.apps.ai.agent.skill.service import AgentSkillService


class AgentSkillPromptBuilder:
    @staticmethod
    def build(skill) -> str:
        return AgentSkillService.build_skill_prompt(skill)
