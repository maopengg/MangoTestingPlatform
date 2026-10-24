from decimal import Decimal

from src.apps.perf.enums import PerfThresholdSeverityEnum


class PerfPerformanceGoalService:
    DEFAULT_P95_MS = 500
    DEFAULT_MAX_ERROR_RATE = Decimal("0.01")
    DEFAULT_MIN_LOAD_ACHIEVEMENT_RATE = Decimal("0.95")

    @classmethod
    def default_payload(cls) -> dict:
        return {
            "template_key": "recommended",
            "p95_ms": cls.DEFAULT_P95_MS,
            "max_error_rate": float(cls.DEFAULT_MAX_ERROR_RATE),
            "min_load_achievement_rate": float(cls.DEFAULT_MIN_LOAD_ACHIEVEMENT_RATE),
        }

    @staticmethod
    def serialize(scenario) -> dict:
        return {
            "template_key": scenario.goal_template_key,
            "p95_ms": scenario.goal_p95_ms,
            "max_error_rate": float(scenario.goal_max_error_rate),
            "min_load_achievement_rate": float(scenario.goal_min_load_achievement_rate),
        }

    @staticmethod
    def to_result_rules(goal: dict) -> list[dict]:
        return [
            {
                "name": "P95 响应时间",
                "scope_type": "global",
                "metric": "p95_ms",
                "operator": "<=",
                "threshold_value": goal["p95_ms"],
                "severity": PerfThresholdSeverityEnum.CRITICAL.value,
            },
            {
                "name": "错误率",
                "scope_type": "global",
                "metric": "error_rate",
                "operator": "<=",
                "threshold_value": goal["max_error_rate"],
                "severity": PerfThresholdSeverityEnum.CRITICAL.value,
            },
            {
                "name": "负载达成率",
                "scope_type": "global",
                "metric": "load_achievement_rate",
                "operator": ">=",
                "threshold_value": goal["min_load_achievement_rate"],
                "severity": PerfThresholdSeverityEnum.CRITICAL.value,
            },
        ]
