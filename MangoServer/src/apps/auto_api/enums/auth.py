from src.common.enums.base import BaseEnum


class ApiAuthTypeEnum(BaseEnum):
    """API授权方式"""
    API = 0
    CUSTOM = 1

    @classmethod
    def obj(cls):
        return {0: "接口登录", 1: "自定义代码"}


class ApiAuthRefreshModeEnum(BaseEnum):
    """API授权刷新方式"""
    PASSIVE = 0
    TIMING = 1
    BOTH = 2
    MANUAL = 3
    EXPIRE_NOTICE = 4

    @classmethod
    def obj(cls):
        return {0: "执行时检测刷新", 1: "定时刷新", 2: "执行时检测+定时刷新", 3: "手动刷新（永久有效）", 4: "到期通知"}


class ApiAuthRefreshStatusEnum(BaseEnum):
    """API授权刷新状态"""
    INIT = 0
    SUCCESS = 1
    FAIL = 2

    @classmethod
    def obj(cls):
        return {0: "未刷新", 1: "刷新成功", 2: "刷新失败"}
