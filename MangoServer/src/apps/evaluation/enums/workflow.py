from src.common.enums.base import BaseEnum


class EvaluationPreparationEnum(BaseEnum):
    NONE = ("none", "无需准备")
    READ = ("read", "读取已有数据")
    CREATE = ("create", "自动创建数据")


class EvaluationSequenceEnum(BaseEnum):
    INDEPENDENT = ("independent", "独立条目")
    CONVERSATION = ("conversation", "多轮对话")
    TIMELINE = ("timeline", "时序执行")


class EvaluationWorkflowStageEnum(BaseEnum):
    PREPARE = ("prepare", "数据准备")
    READY = ("ready", "就绪检查")
    REFERENCE = ("reference", "标准答案准备")
    BEFORE_TURN = ("before_turn", "轮次前执行")
    AFTER_TURN = ("after_turn", "轮次后执行")
    CLEANUP = ("cleanup", "数据清理")


class EvaluationWorkflowScopeEnum(BaseEnum):
    EXECUTION = ("execution", "整次执行")
    GROUP = ("group", "每个用户或会话组")
    ITEM = ("item", "每条数据")


class EvaluationWorkflowActionEnum(BaseEnum):
    API = ("api_info", "接口管理")
    SCRIPT = ("script", "Python 脚本")
    SQL = ("sql", "SQL 查询")
    FACTORY = ("factory", "数据工厂")


class EvaluationTurnKindEnum(BaseEnum):
    TEST = ("test", "测试问题")
    MATERIAL = ("material", "写入材料")
