from src.common.enums.base import BaseEnum


class EvaluationAnswerVerdictEnum(BaseEnum):
    CORRECT = ("correct", "正确")
    HALLUCINATION = ("hallucination", "幻觉")
    OMISSION = ("omission", "遗漏")
