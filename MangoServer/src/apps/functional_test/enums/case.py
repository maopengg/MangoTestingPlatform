from src.common.enums.base import BaseEnum


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


class FunctionalCaseStatusEnum(BaseEnum):
    DRAFT = 0
    ENABLED = 1
    DISABLED = 2

    @classmethod
    def obj(cls):
        return {0: "草稿", 1: "启用", 2: "停用"}


class ManualTestCaseVersionSourceEnum(BaseEnum):
    BASELINE = 0
    LIBRARY = 1
    EXECUTION = 2
    REQUIREMENT_SYNC = 3

    @classmethod
    def obj(cls):
        return {0: "历史基线", 1: "用例库编辑", 2: "执行同步", 3: "需求同步"}
