# -*- coding: utf-8 -*-
from src.common.enums import BaseEnum


class ManualTestTypeEnum(BaseEnum):
    MANUAL = 0
    API = 1
    UI = 2
    PYTEST = 3
    PERF = 4
    MONITORING = 5

    @classmethod
    def obj(cls):
        return {
            0: "手工测试",
            1: "API自动化",
            2: "UI自动化",
            3: "Pytest自动化",
            4: "性能测试",
            5: "监控任务",
        }


class ManualTestSourceTypeEnum(BaseEnum):
    MANUAL = 0
    FEISHU = 1
    IMPORT = 2

    @classmethod
    def obj(cls):
        return {0: "手工录入", 1: "飞书文档", 2: "文件导入"}


class ManualTestSyncStatusEnum(BaseEnum):
    NOT_SYNCED = 0
    SYNCED = 1
    CHANGED = 2
    SYNC_FAILED = 3

    @classmethod
    def obj(cls):
        return {0: "未同步", 1: "已同步", 2: "有变更", 3: "同步失败"}


class ManualTestChangeStatusEnum(BaseEnum):
    UNCHANGED = 0
    ADDED = 1
    CHANGED = 2
    REMOVED = 3

    @classmethod
    def obj(cls):
        return {0: "无变化", 1: "新增", 2: "已变更", 3: "来源已移除"}


class ManualTestAutomationImpactStatusEnum(BaseEnum):
    NONE = 0
    PENDING_REVIEW = 1
    NEED_OPTIMIZE = 2
    OPTIMIZED = 3
    IGNORED = 4

    @classmethod
    def obj(cls):
        return {
            0: "无影响",
            1: "待确认",
            2: "需优化",
            3: "已优化",
            4: "已忽略",
        }


class ManualTestAutomationTypeEnum(BaseEnum):
    API = 0
    UI = 1
    PYTEST = 2

    @classmethod
    def obj(cls):
        return {0: "API自动化", 1: "UI自动化", 2: "Pytest自动化"}


class ManualTestRelationTypeEnum(BaseEnum):
    GENERATED = 0
    BOUND = 1
    MANUAL = 2

    @classmethod
    def obj(cls):
        return {0: "AI生成", 1: "绑定已有", 2: "手工维护"}


class ManualTestOptimizeStatusEnum(BaseEnum):
    NORMAL = 0
    NEED_OPTIMIZE = 1
    OPTIMIZING = 2
    OPTIMIZED = 3
    IGNORED = 4

    @classmethod
    def obj(cls):
        return {
            0: "正常",
            1: "需优化",
            2: "优化中",
            3: "已优化",
            4: "已忽略",
        }


class FunctionalTestContextKeyEnum(BaseEnum):
    REQUIREMENT_DOC = 0
    DEVELOPMENT_DESIGN = 1
    API_DOC = 2
    DEVELOPMENT_CODE = 3
    SQL_QUERY = 4
    RAW_CASE_DOC = 5
    PLATFORM_CASE = 6
    PAGE_DATA = 7
    TEST_UNDERSTANDING = 8

    @classmethod
    def obj(cls):
        return {
            0: "需求文档",
            1: "开发设计",
            2: "接口文档",
            3: "开发代码",
            4: "SQL语句",
            5: "原始Case文档",
            6: "测试平台用例",
            7: "页面数据",
            8: "测试理解",
        }


class FunctionalTestContextContentTypeEnum(BaseEnum):
    TEXT = 0
    URL = 1
    FILE = 2
    IMAGE = 3

    @classmethod
    def obj(cls):
        return {0: "文本", 1: "URL", 2: "文件", 3: "图片"}


class FunctionalTestContextUrlTypeEnum(BaseEnum):
    NORMAL = 0
    FEISHU = 1

    @classmethod
    def obj(cls):
        return {0: "普通URL", 1: "飞书文档"}


class FunctionalTestContextParseStatusEnum(BaseEnum):
    NOT_PARSED = 0
    PARSING = 1
    SUCCESS = 2
    FAILED = 3
    UNSUPPORTED = 4

    @classmethod
    def obj(cls):
        return {
            0: "未解析",
            1: "解析中",
            2: "解析成功",
            3: "解析失败",
            4: "暂不支持",
        }
