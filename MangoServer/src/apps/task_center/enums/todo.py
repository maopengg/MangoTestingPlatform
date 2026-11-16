from src.common.enums.base import BaseEnum


class WorkbenchTodoSourceTypeEnum(BaseEnum):
    UI_AUTH = 1
    API_AUTH = 2
    DATA_FACTORY_ENTITY = 3
    DATA_FACTORY_EXECUTION = 4
    SQL_EXECUTION = 5
    API_CASE = 6
    TEST_REPORT = 7

    @classmethod
    def obj(cls):
        return {
            1: "前端授权",
            2: "服务授权",
            3: "数据工厂模型",
            4: "数据工厂执行记录",
            5: "SQL执行记录",
            6: "API Case",
            7: "测试报告",
        }


class WorkbenchTodoEventTypeEnum(BaseEnum):
    AUTH_EXPIRING = 1
    AUTH_EXPIRED = 2
    AUTH_REFRESH_FAILED = 3
    DATA_FACTORY_SCHEMA_INVALID = 4
    DATA_FACTORY_SCHEMA_REVIEW = 5
    DATA_FACTORY_CLEANUP_FAILED = 6
    SLOW_SQL = 7
    DATA_FACTORY_CLEANUP_REQUIRED = 8
    API_CASE_PREPUBLICATION_REVIEW = 9
    REPORT_INFRASTRUCTURE_BLOCKED = 10

    @classmethod
    def obj(cls):
        return {
            1: "授权即将到期",
            2: "授权已过期",
            3: "授权刷新失败",
            4: "数据模型无效",
            5: "数据模型结构待确认",
            6: "数据工厂清理失败",
            7: "慢SQL",
            8: "数据工厂需要清理",
            9: "API Case 预发布待审核",
            10: "测试执行平台受阻",
        }


class WorkbenchTodoSeverityEnum(BaseEnum):
    WARNING = 1
    DANGER = 2

    @classmethod
    def obj(cls):
        return {1: "警告", 2: "异常"}


class WorkbenchTodoStatusEnum(BaseEnum):
    PENDING = 0
    HANDLED = 1

    @classmethod
    def obj(cls):
        return {0: "待处理", 1: "已处理"}
