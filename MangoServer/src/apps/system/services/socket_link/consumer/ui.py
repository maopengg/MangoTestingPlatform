# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from mangotools.contracts import TestSuiteDetailResultContract

from src.apps.auto_ui.schemas.execution import UiPageStepResult, UiCaseExecutionResult
from src.apps.auto_ui.services.executor_slot import ExecutorSlotLeaseService
from src.apps.auto_ui.services.test_report_writing import TestReportWriting
from src.apps.gray_config.services.execution_runner import GrayCaseExecutionRunner
from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
from src.apps.test_center.services.test_suite.update_test_suite import UpdateTestSuite
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
        UpdateTestSuite.update_test_suite_details(result)
        cls._finish_executor_slot(getattr(result, "result_data", None))
        GrayCaseExecutionRunner.restore_by_config_ids(
            getattr(result.result_data, "gray_config_ids", None),
            {
                "test_suite_id": result.test_suite,
                "test_suite_detail_id": result.id,
                "case_type": result.type,
                "case_id": getattr(result.result_data, "id", None),
                "case_name": getattr(result.result_data, "name", None),
                "_test_env": getattr(result.result_data, "test_env", None),
            },
            getattr(result.result_data, "gray_execution_log_ids", None),
        )

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
        GrayCaseExecutionRunner.restore_by_config_ids(
            result.gray_config_ids,
            {
                "case_type": 2,
                "case_id": result.id,
                "case_name": result.name,
                "_test_env": result.test_env,
            },
            result.gray_execution_log_ids,
        )

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
