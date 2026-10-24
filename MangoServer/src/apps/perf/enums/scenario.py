from src.common.enums.base import BaseEnum


class PerfScenarioExecutionModeEnum(BaseEnum):
    SEQUENTIAL = ("sequential", "顺序")


class PerfEngineEnum(BaseEnum):
    K6 = ("k6", "k6")


class PerfNodeFailurePolicyEnum(BaseEnum):
    STRICT = ("strict", "严格")
    CONTINUE = ("continue", "满足最小节点后继续")
