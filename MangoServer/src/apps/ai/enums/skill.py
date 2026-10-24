from src.common.enums.base import BaseEnum


class AiSkillStatusEnum(BaseEnum):
    DRAFT = 0
    PUBLISHED = 1
    DISABLED = 2
    ARCHIVED = 3

    @classmethod
    def obj(cls):
        return {0: "草稿", 1: "已发布", 2: "已停用", 3: "已归档"}


class AiSkillTypeEnum(BaseEnum):
    FUNCTIONAL_TEST = 0
    API_AUTOMATION = 1
    UI_AUTOMATION = 2

    @classmethod
    def obj(cls):
        return {0: "功能测试", 1: "API自动化", 2: "UI自动化"}
