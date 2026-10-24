from collections.abc import Mapping
from typing import Any

from src.apps.perf.exceptions import (
    PERF_SCENARIO_REQUEST_CONFIG_PERF_REQUIRED,
    PERF_SCENARIO_PERF_REQUIRED,
    PerfError,
)


class PerfScenarioConfigurationService:
    REPLACEMENT_FIELDS = {
        "source_case_release_id": "来源API自动化 Case",
        "load_config": "负载配置",
        "performance_goal": "性能目标",
    }

    @classmethod
    def validate_replacement(
            cls,
            payload: Mapping[str, Any],
            **_kwargs,
    ) -> None:
        missing_fields = [label for field, label in cls.REPLACEMENT_FIELDS.items() if field not in payload]
        if missing_fields:
            raise PerfError(PERF_SCENARIO_REQUEST_CONFIG_PERF_REQUIRED, value=("、".join(missing_fields),))

        if not payload.get("load_config"):
            raise PerfError(PERF_SCENARIO_PERF_REQUIRED, value=("负载配置",))
