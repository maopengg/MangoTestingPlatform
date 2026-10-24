from enum import Enum

from src.common.prompts.ai_agent_role import AI_AGENT_ROLE_PROMPTS


class AgentRole(str, Enum):
    BUSINESS_TEST_EXPERT = "business_test_expert"
    API_AUTOMATION_EXPERT = "api_automation_expert"

    @classmethod
    def labels(cls) -> dict[str, str]:
        return {
            cls.BUSINESS_TEST_EXPERT.value: "业务测试专家",
            cls.API_AUTOMATION_EXPERT.value: "API自动化测试专家",
        }

    @classmethod
    def prompts(cls) -> dict[str, str]:
        return AI_AGENT_ROLE_PROMPTS

    @classmethod
    def snapshot(cls, role: str) -> dict:
        role = cls.normalize(role)
        return {
            "key": role,
            "name": cls.labels().get(role, role),
            "prompt": cls.prompts().get(role, ""),
        }

    @classmethod
    def normalize(
            cls,
            role: str | None,
            default: str | None = None,
            *,
            allowed_roles: list[str] | None = None,
    ) -> str:
        prompts = cls.prompts()
        allowed = set(allowed_roles or prompts.keys())
        role_value = role.value if isinstance(role, cls) else role
        if role_value in prompts and role_value in allowed:
            return role_value
        fallback = default or cls.BUSINESS_TEST_EXPERT.value
        fallback_value = fallback.value if isinstance(fallback, cls) else fallback
        return fallback_value if fallback_value in allowed else next(iter(allowed), fallback_value)

    @classmethod
    def prompt(cls, role: str | None, default: str | None = None) -> str:
        return cls.prompts().get(cls.normalize(role, default), "")
