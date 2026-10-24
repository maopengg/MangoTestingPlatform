from src.common.enums.base import BaseEnum


class EvaluationItemSourceEnum(BaseEnum):
    MANUAL = ("manual", "手动填写")
    SQL = ("sql", "SQL 查询")
    FACTORY = ("factory", "数据工厂")
    API = ("api_info", "参考接口查询")
