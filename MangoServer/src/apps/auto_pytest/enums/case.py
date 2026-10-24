from src.common.enums.base import BaseEnum


class PytestCasePublicationStatusEnum(BaseEnum):
    UNPUBLISHED = 'unpublished', '未发布'
    PREPUBLISHED = 'prepublished', '预发布'
    PUBLISHED = 'published', '已发布'
