# -*- coding: utf-8 -*-


class AgentRole:
    BUSINESS_TEST_EXPERT = "business_test_expert"
    API_AUTOMATION_EXPERT = "api_automation_expert"

    LABELS = {
        BUSINESS_TEST_EXPERT: "业务测试专家",
        API_AUTOMATION_EXPERT: "API自动化测试专家",
    }

    PROMPTS = {
        BUSINESS_TEST_EXPERT: "你是一位业务测试专家，负责基于需求、原始用例和补充要求完成完整的功能测试设计。",
        API_AUTOMATION_EXPERT: "你是一位 API 自动化测试专家，请使用 Skill 的规则和 MCP 工具完成当前功能测试用例的 API 自动化。",
    }

    @classmethod
    def snapshot(cls, role: str) -> dict:
        role = cls.normalize(role)
        return {
            "key": role,
            "name": cls.LABELS.get(role, role),
            "prompt": cls.PROMPTS.get(role, ""),
        }

    @classmethod
    def normalize(cls, role: str | None, default: str | None = None) -> str:
        if role in cls.PROMPTS:
            return role
        return default or cls.BUSINESS_TEST_EXPERT

    @classmethod
    def prompt(cls, role: str | None, default: str | None = None) -> str:
        return cls.PROMPTS.get(cls.normalize(role, default), "")
