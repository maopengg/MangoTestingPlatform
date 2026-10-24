from dataclasses import dataclass, field
from typing import Any


@dataclass
class ApiCaseExecutionContext:
    source_type: int
    user_id: int | None
    test_env: int | None
    case_id: int
    case_name: str | None = None
    test_suite_id: int | None = None
    test_suite_detail_id: int | None = None
    parametrize: dict | list | None = None
    worker_name: str | None = None
    summary: dict[str, Any] = field(default_factory=dict)
