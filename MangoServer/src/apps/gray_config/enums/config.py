from src.common.enums.base import BaseEnum


class GrayConfigTypeEnum(BaseEnum):
    YAML = 1
    SQL = 2
    CODE = 3

    @classmethod
    def obj(cls):
        return {cls.YAML.value: "YAML", cls.SQL.value: "SQL", cls.CODE.value: "代码"}


class GrayActionEnum(BaseEnum):
    ENABLE = "enable"
    DISABLE = "disable"
    RESTORE = "restore"

    @classmethod
    def obj(cls):
        return {
            cls.ENABLE.value: "开启",
            cls.DISABLE.value: "关闭",
            cls.RESTORE.value: "恢复",
        }
