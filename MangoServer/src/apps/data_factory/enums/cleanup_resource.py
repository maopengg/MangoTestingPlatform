from src.common.enums.base import BaseEnum


class EsCleanupModeEnum(BaseEnum):
    VERIFY = ('verify', '仅等待并验证消失')
    DELETE_AND_VERIFY = ('delete_and_verify', '精确删除并回查')
