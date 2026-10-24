from src.common.enums.base import BaseEnum


class EvaluationStatusEnum(BaseEnum):
    DRAFT = ("draft", "草稿")
    ENABLED = ("enabled", "启用")
    ARCHIVED = ("archived", "已归档")


class EvaluationVersionStatusEnum(BaseEnum):
    DRAFT = ("draft", "草稿")
    PUBLISHED = ("published", "已发布")
    DEPRECATED = ("deprecated", "已废弃")

