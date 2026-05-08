# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂枚举

from src.enums import BaseEnum


class DataFactorySourceModeEnum(BaseEnum):
    """数据源模式"""
    FIXED_DATABASE = 1
    FOLLOW_ENVIRONMENT = 2

    @classmethod
    def obj(cls):
        return {1: "固定数据库", 2: "跟随执行环境"}


class DataFactoryOperationTypeEnum(BaseEnum):
    """创建/删除方式"""
    API = 1
    SQL = 2
    FUNCTION = 3

    @classmethod
    def obj(cls):
        return {1: "API", 2: "SQL", 3: "自定义函数"}


class DataFactoryGeneratorTypeEnum(BaseEnum):
    """字段生成方式"""
    SKIP = 0
    FIXED = 1
    RANDOM_STRING = 2
    RANDOM_INTEGER = 3
    RANDOM_DECIMAL = 4
    NOW = 5
    RELATIVE_TIME = 6
    UUID = 7
    AUTO_CODE = 8
    ENUM = 9
    EXPRESSION = 10
    DEPENDENCY_FIELD = 11
    SQL_QUERY = 12
    FUNCTION = 13

    @classmethod
    def obj(cls):
        return {
            0: "跳过",
            1: "固定值",
            2: "随机字符串",
            3: "随机整数",
            4: "随机小数",
            5: "当前时间",
            6: "相对时间",
            7: "UUID",
            8: "自动编号",
            9: "枚举值",
            10: "表达式",
            11: "依赖实体字段",
            12: "SQL查询结果",
            13: "测试数据方法",
        }


class DataFactoryCleanupStrategyEnum(BaseEnum):
    """清理策略"""
    EXECUTION_END = 1
    MANUAL = 2
    NONE = 3

    @classmethod
    def obj(cls):
        return {1: "执行结束", 2: "手动清理", 3: "不清理"}


class DataFactoryExecutionSourceEnum(BaseEnum):
    """执行来源"""
    TEMPLATE_DEBUG = 1
    MANUAL = 2
    SYSTEM = 3

    @classmethod
    def obj(cls):
        return {1: "模板调试", 2: "手动执行", 3: "系统调用"}


class DataFactoryExecutionStageEnum(BaseEnum):
    """执行阶段"""
    DEBUG = 1
    CREATE = 2
    CLEANUP = 3

    @classmethod
    def obj(cls):
        return {1: "调试", 2: "创建", 3: "清理"}


class DataFactoryExecutionStatusEnum(BaseEnum):
    """执行状态"""
    PENDING = 1
    SUCCESS = 2
    FAIL = 3
    PROCEED = 4

    @classmethod
    def obj(cls):
        return {1: "待执行", 2: "成功", 3: "失败", 4: "进行中"}


class DataFactoryCleanupStatusEnum(BaseEnum):
    """清理状态"""
    NOT_CLEANED = 0
    SUCCESS = 1
    FAIL = 2
    SKIPPED = 3

    @classmethod
    def obj(cls):
        return {0: "未清理", 1: "已清理", 2: "清理失败", 3: "跳过清理"}
