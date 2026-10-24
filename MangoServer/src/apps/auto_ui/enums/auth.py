from src.common.enums.base import BaseEnum


class UiAuthTypeEnum(BaseEnum):
    """UI授权方式"""
    MANUAL = 0
    AUTO = 1
    API = 2
    PAGE_STEP = 3
    CUSTOM = 4

    @classmethod
    def obj(cls):
        return {0: "手动复制", 1: "自动授权", 2: "接口转入", 3: "选择页面步骤", 4: "自定义代码"}


class UiAuthRefreshModeEnum(BaseEnum):
    """UI授权刷新方式"""
    MANUAL = 0
    TIMING = 1
    EXPIRE_NOTICE = 2

    @classmethod
    def obj(cls):
        return {0: "手动刷新", 1: "定时刷新", 2: "到期通知"}


class UiAuthRefreshStatusEnum(BaseEnum):
    """UI授权刷新状态"""
    INIT = 0
    SUCCESS = 1
    FAIL = 2

    @classmethod
    def obj(cls):
        return {0: "未刷新", 1: "刷新成功", 2: "刷新失败"}
