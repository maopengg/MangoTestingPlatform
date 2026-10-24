from mangotools.contracts import PytestExecutionResult

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from src.apps.auto_pytest.models import PytestCase
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.common.decorators.retry import async_task_db_connection
from src.common.logging import log


class PtestTestReportWriting:

    @classmethod
    @async_task_db_connection()
    def update_pytest_test_case(cls, data: PytestExecutionResult):
        log.ui.debug(f'开始写入Pytest用例<{data.name}>测试结果，用例的测试状态是：{data.status}')
        case = PytestCase.objects.get(id=data.id)
        case.status = data.status
        case.save(update_fields=['status'])
        ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_PAGE,
            target_type=ExecutionResultService.TARGET_PYTEST_CASE,
            target_id=case.id,
            status=data.status,
            result_data=data.result_data,
            error_message=getattr(data, 'error_message', None),
            source_snapshot=data.source_snapshot,
            task_id=data.dispatch_id,
        )
