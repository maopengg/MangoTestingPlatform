from src.common.enums.base import BaseEnum


class ApiParameterTypeEnum(BaseEnum):
    """api请求参数的类型"""
    params = 0
    data = 1
    json = 2
    file = 3

    @classmethod
    def obj(cls):
        return {0: "参数", 1: "表单", 2: "json", 3: "文件"}


class ApiBodyTypeEnum(BaseEnum):
    """API请求体类型"""
    NONE = "none"
    JSON = "json"
    FORM = "form"
    RAW = "raw"
    MULTIPART = "multipart"

    @classmethod
    def obj(cls):
        return {
            "none": "无请求体",
            "json": "JSON",
            "form": "表单",
            "raw": "Raw文本",
            "multipart": "Multipart",
        }
