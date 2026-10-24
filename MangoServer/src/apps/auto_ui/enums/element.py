from src.common.enums.base import BaseEnum


class ElementExpEnum(BaseEnum):
    """元素定位方式枚举"""
    XPATH = 0
    # TEST_ID = 1
    LOCATOR = 2
    TEXT = 3
    PLACEHOLDER = 4
    # LABEL = 5
    # TITLE = 6
    # ROLE = 7
    # AIT_TEXT = 8
    CSS = 9
    # APP专属
    DESCRIPTION = 11
    BOUNDS = 12
    # PERCENTAGE = 13
    RESOURCE_ID = 14
    IOS_ACCESSIBILITY_ID = 20
    IOS_PREDICATE = 21
    IOS_CLASS_CHAIN = 22
    IOS_CLASS_NAME = 23

    @classmethod
    def obj(cls):
        return {
            0: "XPATH",
            # 1: "W_TestID",
            2: "通用定位器",
            3: "WEB_文本",
            4: "WEB_占位符",
            # 5: "W_标签",
            # 6: "W_标题",
            # 7: "W_ROLE",
            # 8: "W_AIT_TEXT",
            9: "WEB_CSS",
            11: "安卓_description",
            12: "安卓_bounds",
            # 13: "A_百分比坐标点击",
            14: "安卓_resourceId",
            20: "iOS_可访问性ID",
            21: "iOS_Predicate",
            22: "iOS_ClassChain",
            23: "iOS_ClassName",
        }


class ElementOperationEnum(BaseEnum):
    """元素操作类型枚举"""
    OPE = 0
    ASS = 1
    SQL = 2
    CUSTOM = 3
    CONDITION = 4
    PYTHON_CODE = 5
    FORCE_WAIT = 6

    @classmethod
    def obj(cls):
        return {
            0: "元素操作",
            1: "断言操作",
            2: "SQL变量",
            3: "自定义变量",
            4: "条件判断",
            5: "python代码",
            6: "强制等待",
        }


class UiElementCheckModeEnum(BaseEnum):
    QUICK = ("quick", "快速扫描")
    DEEP = ("deep", "深度扫描")
    REGION = ("region", "区域扫描")
