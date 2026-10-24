from src.common.enums.base import BaseEnum


class PytestSourceStatusEnum(BaseEnum):
    ACTIVE = (0, '源码正常')
    MODIFIED = (1, '源码有更新')
    MISSING = (2, '源码已缺失')
    PARSE_FAILED = (3, '解析失败')
    CONFLICT = (4, '来源冲突')


class PytestAssetStatusEnum(BaseEnum):
    DRAFT = (0, '草稿')
    PUBLISHED = (1, '已发布')
    DISABLED = (2, '已停用')
    ARCHIVED = (3, '已归档')
    IGNORED = (4, '已忽略')
