# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-25 15:04
# @Author : 毛鹏
from django.db import transaction
from mangotools.contracts import SocketEnvelopeContract
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_pytest.services.reporting.test_report_writing import PtestTestReportWriting
from src.apps.auto_ui.services.reporting.test_report_writing import TestReportWriting
from src.apps.system.enums import ClientTypeEnum
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.test_center.services.reporting.test_suite.send_notice import SendNotice
from src.apps.test_center.services.reporting.test_suite.timeout_recovery import TestSuiteTimeoutRecoveryService
from src.apps.test_center.services.reporting.testcounter import TestCounter
from src.common.logging import log


class UpdateTestSuite:

    @classmethod
    def update_test_suite(cls, test_suite_id: int, status: int):
        return bool(TestSuite.objects.filter(id=test_suite_id).exclude(
            status=TaskEnum.STOPPED.value,
        ).filter(retained_summary__isnull=True).update(status=status))

    @classmethod
    def update_test_suite_details_status(cls, test_suite_details_id: int, status, msg):
        with transaction.atomic():
            test_suite_detail = TestSuiteDetails.objects.select_related('test_suite').get(
                id=test_suite_details_id
            )
            test_suite = TestSuite.objects.select_for_update().get(id=test_suite_detail.test_suite_id)
            from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
            test_suite_detail.refresh_from_db()
            if (test_suite.status == TaskEnum.STOPPED.value
                    or TestSuiteInfrastructureService.is_blocked(test_suite_detail.summary_data)):
                return False
            test_suite_detail.status = status
            test_suite_detail.error_message = msg
            test_suite_detail.save()
            return True

    @classmethod
    def update_test_suite_details(cls, data: TestSuiteDetailResultSchema):
        log.system.debug(f'开始更新测试套数据：{data.model_dump_json()}')
        if data.type == TestCaseTypeEnum.UI:
            result_data = [i.model_dump() for i in data.result_data.steps]
        elif data.type == TestCaseTypeEnum.API:
            result_data = [i.model_dump() for i in data.result_data.steps]
        else:
            result_data = data.result_data.result_data

        original_detail = TestSuiteDetails.objects.get(id=data.id, test_suite_id=data.test_suite)
        pytest_count = TestCounter.completed_pytest_count(data.result_data) if data.type == TestCaseTypeEnum.PYTEST else None
        result_data = TestSuiteExecutionResultService.normalize_detail_result_data(original_detail, result_data)
        prepared = ExecutionResultService.prepare_result_payload(
            result_data,
            TestSuiteExecutionResultService.target_type_by_detail(original_detail),
            original_detail.case_id, data.test_suite, data.id,
        )

        def persist():
            test_suite = TestSuite.objects.select_for_update().get(id=data.test_suite)
            if test_suite.retained_summary:
                return None
            if test_suite.status == TaskEnum.STOPPED.value:
                log.system.info(
                    f'忽略已停止测试报告的晚到结果：test_suite={data.test_suite}, detail={data.id}'
                )
                return None
            test_suite_detail = TestSuiteDetails.objects.select_for_update().get(
                id=data.id, test_suite_id=data.test_suite,
            )
            if data.type == TestCaseTypeEnum.API:
                meta = (test_suite_detail.summary_data or {}).get('meta', {}) if isinstance(test_suite_detail.summary_data, dict) else {}
                if ((data.attempt is not None and data.attempt != test_suite_detail.retry)
                        or (meta.get('recovery_history') and data.attempt is None)):
                    return None
            from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
            from src.apps.test_center.services.reporting.test_suite.recovery import ReportRecoveryService
            from src.apps.test_center.enums.reporting import ReportExecutionPhaseEnum
            control = ReportRecoveryService.read(test_suite_detail.summary_data)
            if control is not None:
                if (data.type == TestCaseTypeEnum.API and data.attempt == control.attempt
                        and control.phase == ReportExecutionPhaseEnum.AUTOMATIC_RECOVERY
                        and test_suite_detail.status == TaskEnum.PROCEED.value
                        and data.status in (TaskEnum.FAIL.value, TaskEnum.SUCCESS.value, TaskEnum.WARNING.value)
                        and data.result_data.execution_finalized is True):
                    # 同轮次结果只作恢复证据；不发布终态、不覆盖新轮次、不提前发送通知。
                    if control.result_id is None:
                        saved = ExecutionResultService.save_result(
                            source_type=ExecutionResultService.SOURCE_REPORT,
                            target_type=ExecutionResultService.TARGET_API_CASE,
                            target_id=test_suite_detail.case_id,
                            test_env=test_suite_detail.test_env,
                            revision_id=test_suite_detail.api_case_revision_id,
                            release_id=test_suite_detail.api_case_release_id,
                            test_suite_id=data.test_suite, test_suite_detail_id=data.id,
                            status=data.status, error_message=data.error_message,
                            trace_id=data.result_data.trace_id, result_data=result_data,
                            prepared_result_payload=prepared,
                        )
                        control.result_id = saved.id
                    control.result_expected = True
                    control.checks += 1
                    ReportRecoveryService.put(test_suite_detail, control)
                    test_suite_detail.save(update_fields=['summary_data', 'update_time'])
                    return test_suite_detail
                return None
            if TestSuiteInfrastructureService.is_blocked(test_suite_detail.summary_data):
                return None
            if TestSuiteTimeoutRecoveryService.is_timeout_terminated(test_suite_detail):
                log.system.info(
                    f'忽略系统超时终止后的晚到结果：test_suite={data.test_suite}, detail={data.id}'
                )
                return None
            test_suite_detail.status = data.status
            if data.type == TestCaseTypeEnum.UI:
                test_suite_detail.error_message = data.error_message
            elif data.type == TestCaseTypeEnum.API:
                test_suite_detail.error_message = data.error_message
            else:
                test_suite_detail.case_name = data.result_data.name
                if pytest_count is not None:
                    test_suite_detail.case_sum = pytest_count
            test_suite_detail.save()
            TestSuiteExecutionResultService.save_result(
                test_suite_detail,
                result_data,
                source_snapshot=(data.result_data.source_snapshot if data.type == TestCaseTypeEnum.PYTEST else None),
                prepared_result_payload=prepared,
            )
            TestCounter.res_main(test_suite_detail.id)
            return test_suite_detail

        test_suite_detail = ExecutionResultService.run_write_transaction(persist)
        if test_suite_detail is None:
            return False

        if data.type == TestCaseTypeEnum.UI:
            TestReportWriting.update_test_case(data.result_data)
        elif data.type == TestCaseTypeEnum.PYTEST:
            PtestTestReportWriting.update_pytest_test_case(data.result_data)

        active_details = TestSuiteDetails.objects.filter(
            test_suite=data.test_suite,
            status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value],
        )
        if not active_details.exists():
            failed_details = TestSuiteDetails.objects.filter(
                test_suite=data.test_suite,
                status=StatusEnum.FAIL.value,
            )
            warning_details = TestSuiteDetails.objects.filter(
                test_suite=data.test_suite,
                status=TaskEnum.WARNING.value,
            )
            if failed_details.exists():
                final_status = StatusEnum.FAIL.value
            elif warning_details.exists():
                final_status = TaskEnum.WARNING.value
            else:
                final_status = StatusEnum.SUCCESS.value
            if final_status != StatusEnum.FAIL.value and TestSuiteDetails.objects.filter(
                    test_suite=data.test_suite, status=TaskEnum.INFRASTRUCTURE_BLOCKED.value).exists():
                final_status = TaskEnum.FAIL.value
            if cls.update_test_suite(data.test_suite, final_status):
                cls.send_test_result(data.test_suite, data.error_message)
        return True

    @classmethod
    def send_test_result(cls, test_suite_id: int, msg: str):
        test_suite = TestSuite.objects.get(id=test_suite_id)
        if test_suite.status == TaskEnum.STOPPED.value:
            from src.apps.task_center.services.scheduling.task_group_execution import (
                ScheduledTaskGroupExecutionService,
            )
            ScheduledTaskGroupExecutionService.complete_test_suite(test_suite_id)
            return
        grouped = SendNotice(test_suite_id).send_test_suite()
        from src.apps.system.services.socket_link.message_service import SocketMessageService
        SocketMessageService.send_socket_data(SocketEnvelopeContract(
            code=200 if test_suite.status else 300,
            msg=f'测试套ID：{test_suite_id} 执行完成，结果：{msg}' if msg else f'测试套ID：{test_suite_id} 执行完成',
            user=test_suite.user.username,
            is_notice=ClientTypeEnum.WEB,
        ))
        from src.apps.test_center.services.reporting.test_suite.retention import TestSuiteRetentionService
        if not grouped:
            TestSuiteRetentionService.cleanup_safely(test_suite_id)
