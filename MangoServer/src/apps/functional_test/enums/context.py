from src.common.enums.base import BaseEnum


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
