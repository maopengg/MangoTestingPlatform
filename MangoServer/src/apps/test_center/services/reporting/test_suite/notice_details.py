from mangotools.enums import TaskEnum, TestCaseTypeEnum
from src.apps.system.schemas.notice import ReportFailureModel

from src.apps.test_center.selectors.report_notice import ReportNoticeSelector
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.test_center.services.reporting.offline_report.renderer import ReportHtmlService
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
from src.common.logging import log


class ReportNoticeDetailsService:
    @classmethod
    def collect(cls, suite_names):
        if not suite_names:
            return [], ''
        try:
            details = ReportNoticeSelector.failed_details(list(suite_names))
            payloads = TestSuiteExecutionResultService.result_map([row.id for row in details if row.summary_data is None])
            rows, incomplete = [], False
            for detail in details:
                data, _ = TestSuiteExecutionResultService.unpack_summary_data(detail.summary_data)
                if data is None and detail.id in payloads:
                    try:
                        data = ExecutionResultService.load_result_data(payloads[detail.id])
                        data = TestSuiteExecutionResultService.normalize_detail_result_data(detail, data)
                        data = TestSuiteExecutionResultService.build_summary_data(detail, data)
                    except Exception as error:
                        incomplete = True
                        log.system.warning(f'通知步骤摘要读取失败：detail={detail.id}, type={type(error).__name__}')
                rows.extend(cls.detail_rows(detail, data, suite_names.get(detail.test_suite_id, '')))
            return rows, '部分步骤明细不可用，请查看完整报告。' if incomplete else ''
        except Exception as error:
            log.system.warning(f'通知失败明细读取失败：type={type(error).__name__}')
            return [], '失败明细暂时不可用，请查看完整报告。'

    @staticmethod
    def failed(item):
        status = item.get('main_status')
        status = item.get('status') if status is None else status
        return status in (TaskEnum.FAIL.value, 'failed', 'broken')

    @classmethod
    def detail_rows(cls, detail, data, task_name=''):
        if detail.type not in (TestCaseTypeEnum.API.value, TestCaseTypeEnum.UI.value, TestCaseTypeEnum.PYTEST.value):
            return []
        from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService
        if TestSuiteInfrastructureService.is_blocked(detail.summary_data):
            return [ReportFailureModel(case_type=detail.type, task_name=cls.text(task_name),
                case_name=cls.text(detail.case_name or f'Case #{detail.case_id}'),
                target_name='执行中断（非业务断言失败）',
                message=cls.text(f'{detail.error_message or "平台未收到完整结果"}；须复核原请求及清理状态后才能重试。'))]
        data = TestSuiteExecutionResultService.normalize_detail_result_data(detail, data)
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        items = [item for item in items if isinstance(item, dict)]
        if detail.type == TestCaseTypeEnum.API.value:
            executed_items = [item for item in items
                              if str(item.get('error_message') or '').strip() != TestSuiteExecutionResultService.SKIP_MESSAGE]
            # 跳过占位可能带有历史失败状态；全部被过滤时不能再补成一条用例级失败通知。
            if items and not executed_items:
                return []
            items = executed_items
        failed = [item for item in items if isinstance(item, dict) and cls.failed(item)]
        rows = []
        for item in failed or [{}]:
            if detail.type == TestCaseTypeEnum.API.value:
                target = item.get('api_info_name') or (f'接口 #{item["api_info_id"]}' if item.get('api_info_id') else '未记录接口名称')
            elif detail.type == TestCaseTypeEnum.UI.value:
                target = item.get('name') or (f'步骤 #{item["id"]}' if item.get('id') else '未记录失败步骤')
            else:
                target = item.get('fullName') or item.get('nodeid') or item.get('name') or '未记录测试标识'
            status_details = item.get('statusDetails')
            message = item.get('error_message') or (status_details.get('message') if isinstance(status_details, dict) else '')
            message = message or detail.error_message or '未记录错误提示，请查看完整执行报告。'
            if detail.type == TestCaseTypeEnum.API.value and str(message).strip() == TestSuiteExecutionResultService.SKIP_MESSAGE:
                continue
            rows.append(ReportFailureModel(case_type=detail.type, task_name=cls.text(task_name),
                case_name=cls.text(detail.case_name or f'Case #{detail.case_id}'),
                target_name=cls.text(target), message=cls.text(message)))
        if len(rows) > 1:
            # 通知按失败 Case 计行；同一 Case 的真实失败步骤保留在同一行中。
            targets = '\n'.join(dict.fromkeys(row.target_name for row in rows))
            messages = '\n'.join(dict.fromkeys(f'{row.target_name}：{row.message}' for row in rows))
            rows[0].target_name = targets
            rows[0].message = messages
        return rows[:1]

    @staticmethod
    def text(value):
        redacted = ReportHtmlService.redact(str(value or ''))
        return str(redacted)
