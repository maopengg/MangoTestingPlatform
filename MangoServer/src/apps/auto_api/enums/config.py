from enum import Enum

from src.common.enums.base import BaseEnum


class ApiConfigObjectTypeEnum(str, Enum):
    API_INFO = "api_info"
    API_CASE = "api_case"


class ApiConfigDraftStatusEnum(BaseEnum):
    """API配置草稿状态"""
    EDITING = "editing"
    READY = "ready"
    ABANDONED = "abandoned"

    @classmethod
    def obj(cls):
        return {
            "editing": "编辑中",
            "ready": "草稿",
            "abandoned": "已放弃",
        }
