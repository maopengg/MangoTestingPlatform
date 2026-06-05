# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂枚举

from src.common.enums import BaseEnum


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
    ENUM = 9
    DEPENDENCY_FIELD = 11
    FUNCTION = 13

    @classmethod
    def obj(cls):
        return {
            0: "跳过",
            1: "固定值",
            2: "随机字符串（长度8）",
            3: "随机整数（1-100）",
            4: "随机小数（1-100，2位）",
            5: "当前时间",
            6: "相对时间",
            7: "UUID",
            9: "枚举值",
            11: "依赖实体字段",
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


class DataFactoryTemplateConfigStatusEnum(BaseEnum):
    """状态模板配置状态"""
    INCOMPLETE = 0
    READY = 1

    @classmethod
    def obj(cls):
        return {0: "待完善", 1: "已就绪"}


class DataFactoryTemplateUsageScopeEnum(BaseEnum):
    """场景模板用途"""
    CASE = 1
    INTERNAL = 2

    @classmethod
    def obj(cls):
        return {1: "用例可直接选择", 2: "仅场景内部引用"}


class DataFactoryExecutionSourceEnum(BaseEnum):
    """执行来源"""
    TEMPLATE_DEBUG = 1
    MANUAL = 2
    SYSTEM = 3
    API_CASE = 4
    API_CASE_PARAMETER = 5
    UI_CASE = 6

    @classmethod
    def obj(cls):
        return {1: "模板调试", 2: "手动执行", 3: "系统调用", 4: "API用例", 5: "API接口场景", 6: "UI用例"}


class DataFactoryCaseSourceTypeEnum(BaseEnum):
    """用例配置来源"""
    API_CASE = 1
    UI_CASE = 2
    API_CASE_PARAMETER = 3

    @classmethod
    def obj(cls):
        return {1: "API用例", 2: "UI用例", 3: "API接口场景"}


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
    FAIL = 0
    SUCCESS = 1
    PENDING = 2
    PROCEED = 3

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "通过", 2: "待开始", 3: "进行中"}


class DataFactoryCleanupStatusEnum(BaseEnum):
    """清理状态"""
    NOT_CLEANED = 0
    SUCCESS = 1
    FAIL = 2
    SKIPPED = 3

    @classmethod
    def obj(cls):
        return {0: "未清理", 1: "已清理", 2: "清理失败", 3: "跳过清理"}
