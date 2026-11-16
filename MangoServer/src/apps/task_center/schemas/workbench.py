from typing import Literal

from pydantic import Field

from src.common.schemas import StrictSchema


class ReportInfrastructureTodoDetails(StrictSchema):
    """报告受阻聚合快照；明细留在原报告，不复制请求或响应。"""

    version: Literal[1] = 1
    test_suite_id: int
    task_id: int | None
    test_env: int
    blocked_count: int = Field(ge=0)
    execution_item_count: int = Field(ge=0)
    scope_fingerprint: str
    report_count: int = Field(ge=1)
    owner_notified: bool = False
    difference_fingerprint: str
    url: str
    fallback_owner_id: int | None
    latest_occurred_at: str
