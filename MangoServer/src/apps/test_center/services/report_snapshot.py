import base64
import json

from django.core.files.storage import default_storage
from django.utils import timezone
from mangotools.enums import TaskEnum
from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.constants import OFFLINE_REPORT_MAX_BYTES
from src.apps.test_center.enums.case import ReportFailureReasonEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.enums.report_delivery import ReportSourceEnum
from src.apps.test_center.exceptions import REPORT_ARTIFACT_INVALID, REPORT_ARTIFACT_RUNNING, REPORT_ARTIFACT_TOO_LARGE, TestCenterError
from src.apps.test_center.models import ExecutionResult, TestSuite, TestSuiteDetails
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService


class ReportSnapshotService:
    @staticmethod
    def suppresses_success_report(suite, details=None):
        if suite.report_retention_policy != ReportRetentionPolicyEnum.ABNORMAL_ONLY.value or suite.status != TaskEnum.SUCCESS.value:
            return False
        if suite.retained_summary:
            return True
        from src.apps.test_center.services.test_suite.retention import TestSuiteRetentionService
        fields = ('status', 'fail', 'warning', 'is_excluded', 'failure_reason', 'failure_description', 'error_message')
        rows = (list(TestSuiteDetails.objects.filter(test_suite_id=suite.id).values(*fields)) if details is None
                else [{field: getattr(row, field) for field in fields} for row in details])
        return TestSuiteRetentionService.eligible(suite, rows)

    @staticmethod
    def display_time(value):
        return (timezone.localtime(value) if timezone.is_aware(value) else value).isoformat(timespec='seconds')

    @classmethod
    def source_product_id(cls, kind, source_id):
        if kind == ReportSourceEnum.SUITE:
            product_id = TestSuite.objects.filter(id=source_id).values_list('project_product_id', flat=True).first()
        else:
            from src.apps.task_center.services.scheduling.task_group_execution import ScheduledTaskGroupExecutionService
            product_id = ScheduledTaskGroupExecutionService.offline_report_product_id(source_id)
        if not product_id:
            raise TestCenterError(REPORT_ARTIFACT_INVALID)
        return product_id

    @classmethod
    def build(cls, kind, source_id, config):
        if kind == ReportSourceEnum.SUITE:
            suites = [cls.suite(source_id, config)]
            first = suites[0]
            counter = first['summary']
            name, result = first['name'], first['result']
        else:
            from src.apps.task_center.services.scheduling.task_group_execution import ScheduledTaskGroupExecutionService
            _, report = ScheduledTaskGroupExecutionService.offline_report_source(source_id)
            suites = [cls.suite(child.test_suite_id, config) if child.test_suite_id else {
                'name': child.task_name, 'result': child.result, 'cases': [],
                'summary': {key: getattr(child, key) for key in ('case_sum', 'success', 'fail', 'warning')},
            } for child in report.children]
            counter = {key: getattr(report, key) for key in ('case_sum', 'success', 'fail', 'warning', 'excluded_count')}
            name, result = report.task_group_name, ('失败' if report.failed_task_count else '告警' if report.warning_task_count else '通过')
            first = {'product': f'{report.project_name} / {report.product_name}', 'environment': report.test_environment, 'started_at': report.planned_at}
        total = counter['case_sum']
        if not total and not counter.get('excluded_count'):
            result = '无有效结果'
        rate = f"{counter['success'] / total * 100:.2f}%" if total else ('100.00%' if counter.get('excluded_count') else '无有效结果')
        return {'version': 1, 'name': name, 'result': result, 'summary': counter, 'rate': rate, 'suites': suites,
                **{key: first[key] for key in ('product', 'environment', 'started_at')},
                'generated_at': cls.display_time(timezone.now())}

    @classmethod
    def suite(cls, suite_id, config):
        suite = TestSuite.objects.select_related('project_product__project', 'tasks').filter(id=suite_id).first()
        if not suite:
            raise TestCenterError(REPORT_ARTIFACT_INVALID)
        queryset = TestSuiteDetails.objects.filter(test_suite_id=suite_id).order_by('create_time', 'id')
        details = list(queryset[:20001])
        if len(details) > 20000:
            raise TestCenterError(REPORT_ARTIFACT_TOO_LARGE)
        if any(row.status in (TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value) for row in details) or suite.status in (TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value):
            raise TestCenterError(REPORT_ARTIFACT_RUNNING)
        counter = TestSuiteSummaryService.counter_data(suite_id)
        status = TestSuiteSummaryService.conclusion_status(suite.status, counter, counter['case_sum'])
        cases = []
        payload_bytes = 0
        durations = dict(ExecutionResult.objects.filter(test_suite_id=suite_id, is_latest=True).values_list('test_suite_detail_id', 'duration')) if config.include_details else {}
        retain_details = config.include_details and not cls.suppresses_success_report(suite, details)
        for row in details if retain_details else []:
            case = {'id': row.case_id, 'name': row.case_name or f'Case {row.case_id}', 'type': TestCaseTypeEnum.get_value(row.type),
                    'status': TaskEnum.get_value(row.status), 'excluded': row.is_excluded, 'error': row.error_message or '',
                    'reason': ReportFailureReasonEnum.get_value(row.failure_reason) or '', 'description': row.failure_description,
                    'duration': durations.get(row.id), 'payload': None, 'images': []}
            if row.status == TaskEnum.FAIL.value:
                data = TestSuiteExecutionResultService.get_result_data(row)
                from src.apps.test_center.services.report_html import ReportHtmlService
                case['payload'] = ReportHtmlService.redact(data)
                if config.include_screenshots:
                    case['images'] = cls.images(data)
                payload_bytes += len(json.dumps(case, ensure_ascii=False, default=str).encode())
                if payload_bytes > OFFLINE_REPORT_MAX_BYTES:
                    raise TestCenterError(REPORT_ARTIFACT_TOO_LARGE)
            cases.append(case)
        # 读取对象存储时不持有数据库锁；结果在生成期间被重试或编辑则放弃本次快照。
        if (not TestSuite.objects.filter(id=suite_id, update_time=suite.update_time, status=suite.status).exists()
                or dict(queryset.values_list('id', 'update_time')) != {row.id: row.update_time for row in details}):
            raise TestCenterError(REPORT_ARTIFACT_RUNNING)
        return {'name': suite.tasks.name if suite.tasks else suite.execution_name or f'执行报告 {suite.id}',
                'product': f'{suite.project_product.project.name} / {suite.project_product.name}',
                'environment': EnvironmentEnum.get_value(suite.test_env), 'started_at': cls.display_time(suite.create_time),
                'result': TaskEnum.get_value(status), 'summary': counter, 'cases': cases}

    @staticmethod
    def images(data):
        # 只读取已存储的图片对象，不请求结果中的 HTTP URL，避免 SSRF。
        found = []
        def visit(item):
            if len(found) >= 3:
                return
            if isinstance(item, dict):
                for key, value in item.items():
                    if key in ('screenshot', 'screenshot_path', 'screenshot_key') and isinstance(value, str) and '://' not in value and not value.startswith('/') and '..' not in value.split('/'):
                        ext = value.rsplit('.', 1)[-1].lower()
                        if ext not in ('png', 'jpg', 'jpeg', 'webp'):
                            continue
                        try:
                            with default_storage.open(value, 'rb') as file:
                                raw = file.read(512001)
                            if len(raw) <= 512000:
                                found.append('data:image/' + ('jpeg' if ext in ('jpg', 'jpeg') else ext) + ';base64,' + base64.b64encode(raw).decode())
                        except (OSError, ValueError):
                            continue
                    else:
                        visit(value)
            elif isinstance(item, list):
                for value in item[:1000]:
                    visit(value)
        visit(data)
        return found
