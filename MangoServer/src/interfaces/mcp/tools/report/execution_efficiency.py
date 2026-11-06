from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from src.apps.test_center.schemas.execution_efficiency import ExecutionEfficiencyQuery
from src.apps.test_center.services.execution_efficiency import ExecutionEfficiencyService
from src.interfaces.mcp.common import current_user, ok


def register_execution_efficiency_tools(mcp):
    @mcp.tool()
    def list_execution_efficiency(
        section: Literal['queue', 'timing', 'anomalies'] = 'queue',
        project_product_id: Annotated[int | None, Field(gt=0)] = None,
        report_id: Annotated[int | None, Field(gt=0)] = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        test_env: list[int] | None = None,
        case_type: list[int] | None = None,
        task_ids: list[int] | None = None,
        task_group_ids: list[int] | None = None,
        page: Annotated[int, Field(ge=1, le=10000)] = 1,
        page_size: Annotated[int, Field(ge=1, le=100)] = 10,
    ) -> dict:
        """只读查询执行效能，不触发执行、不修改报告或并发。

        queue=当前排队报告，anomalies=当前超时/结果不一致线索，不受历史日期限制。
        timing=时间内创建报告的API耗时概览及慢执行尝试分页；默认最近24小时，最多31天。
        每个慢项是一条执行尝试，不等于不同Case；阶段耗时已去除嵌套重叠。
        UI/Pytest仅提供已有状态计数；异常线索不代表已确认的平台故障。
        超过查询保护上限时请缩小项目、报告或时间范围，不会静默抽样。
        """
        values = dict(section=section, project_product_id=project_product_id, report_id=report_id,
                      test_env=test_env or [], case_type=case_type or [], task_ids=task_ids or [],
                      task_group_ids=task_group_ids or [], page=page, page_size=page_size)
        if start_at is not None:
            values['start_at'] = start_at
        if end_at is not None:
            values['end_at'] = end_at
        data = ExecutionEfficiencyService.query(current_user(), ExecutionEfficiencyQuery(**values))
        if section == 'timing':
            items = data.pop('slow_cases')
            data.pop('trend')
            data.pop('slow_reports')
            offset = (page - 1) * page_size
            data.update(items=items[offset:offset + page_size], count=len(items), page=page, page_size=page_size)
        return ok(data)
