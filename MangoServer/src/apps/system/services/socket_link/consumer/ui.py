# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from mangotools.contracts import TestSuiteDetailResultContract

from src.apps.auto_ui.schemas.execution import UiPageStepResult, UiCaseExecutionResult
from src.apps.auto_ui.services.execution.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.reporting.test_report_writing import TestReportWriting
from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
from src.apps.test_center.services.reporting.test_suite.update_test_suite import UpdateTestSuite
from src.common.decorators.retry import async_task_db_connection


class UIConsumer:

    @classmethod
    def u_live_workspace_status(cls, data: dict):
        from src.apps.auto_ui.services.live_stream.workspace_service import LiveWorkspaceService

        LiveWorkspaceService.update_workspace_status(
            str(data.get('workspace_id') or ''),
            str(data.get('status') or ''),
            str(data.get('message') or ''),
        )

    @classmethod
    @async_task_db_connection()
    def u_page_steps(cls, data: dict):
        cls.save_page_steps_result(data)

    @classmethod
    def save_page_steps_result(cls, data: dict):
        """保存页面步骤结果；统一任务结果在已有事务内直接调用该入口。"""
        result = UiPageStepResult(**data)
        TestReportWriting.update_page_step_status(result)
        if (
                getattr(result, "is_final", False)
                and not getattr(result, "case_step_details_id", None)
        ):
            cls._finish_executor_slot(result)

    @classmethod
    @async_task_db_connection()
    def u_test_suite_details(cls, data: dict):
        result = TestSuiteDetailResultSchema.from_contract(TestSuiteDetailResultContract.model_validate(data))
        if isinstance(result.result_data, UiCaseExecutionResult):
            from mangotools.enums import TaskEnum
            from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
            from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
            from src.apps.test_center.enums import TestCaseTypeEnum
            failures = []
            if result.result_data.data_factory_auto_cleanup_execution_ids:
                with DataFactoryCleanupScheduleService.report_scope(
                        result.id, suite_id=result.test_suite, case_id=result.result_data.id,
                        case_type=TestCaseTypeEnum.UI.value):
                    failures = TestReportWriting.cleanup_data_factory(result.result_data)
            if (result.result_data.data_factory_auto_cleanup_execution_ids and TaskCenterQuerySelector.ui_cleanup_failed(
                    result.result_data.id, result.result_data.execution_id,
                    result.result_data.data_factory_auto_cleanup_execution_ids)):
                failures.append('原执行的数据工厂清理失败；后续补清不能替代原执行通过')
            if failures:
                result.status = result.result_data.status = TaskEnum.FAIL.value
                result.error_message = result.result_data.error_message = '; '.join(
                    filter(None, [result.error_message, *failures]))[:2048]
        UpdateTestSuite.update_test_suite_details(result)
        cls._finish_executor_slot(getattr(result, "result_data", None))

    @classmethod
    @async_task_db_connection()
    def u_test_case(cls, data: dict):
        cls.save_test_case_result(data)

    @classmethod
    def save_test_case_result(cls, data: dict):
        """保存 UI Case 结果；不额外创建异步数据库重试边界。"""
        result = UiCaseExecutionResult(**data)
        TestReportWriting.update_test_case(result)
        cls._finish_executor_slot(result)

    @staticmethod
    def _finish_executor_slot(data) -> None:
        if data is None:
            return
        getter = data.get if isinstance(data, dict) else lambda key: getattr(data, key, None)
        connection_id = getter("executor_connection_id")
        slot_id = getter("slot_id")
        if connection_id and slot_id:
            execution_id = (
                    getter("execution_id")
                    or getter("workspace_id")
                    or getter("check_id")
                    or getter("id")
            )
            ExecutorSlotLeaseService.set_running(
                str(connection_id),
                str(slot_id),
                False,
                execution_id=str(execution_id) if execution_id is not None else None,
            )
