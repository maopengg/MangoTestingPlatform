import json
from typing import Any

from django.core.files.storage import default_storage
from django.utils import timezone
from src.common.logging import log
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.models import ApiCaseDetailedParameter
from src.apps.auto_api.schemas.execution import ApiCaseStepResult, ApiExecutionRequest
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import ExecutionResult, TestSuite, TestSuiteDetails
from src.apps.test_center.services.execution_result import ExecutionResultService


class TestSuiteExecutionResultService:
    @classmethod
    def save_stopped_api_recovery(cls, detail_id, result):
        original = TestSuiteDetails.objects.get(id=detail_id)
        result_data = cls.normalize_detail_result_data(original, [step.model_dump() for step in result.steps])
        prepared = ExecutionResultService.prepare_result_payload(
            result_data, cls.target_type_by_detail(original), original.case_id, original.test_suite_id, original.id,
        )

        def persist():
            suite = TestSuite.objects.select_for_update().get(id=original.test_suite_id)
            if suite.status != TaskEnum.STOPPED.value or suite.retained_summary:
                return
            detail = TestSuiteDetails.objects.select_for_update().get(id=detail_id)
            if detail.status != TaskEnum.STOPPED.value:
                return
            # 仅补存恢复证据，不将停止状态或整份报告改回成功/失败。
            cls.save_result(detail, result_data, prepared_result_payload=prepared)

        ExecutionResultService.run_write_transaction(persist)

    DEFAULT_CASE_HISTORY_LIMIT = 20
    SKIP_MESSAGE = '该用例前置步骤失败，未被执行'
    HISTORY_SOURCE_CURRENT_REPORT = 'current_report'
    HISTORY_SOURCE_OTHER_REPORT = 'other_report'
    HISTORY_SOURCE_CASE = 'case'
    HISTORY_SOURCE_NAMES = {
        HISTORY_SOURCE_CURRENT_REPORT: '本测试报告',
        HISTORY_SOURCE_OTHER_REPORT: '其他测试报告',
        HISTORY_SOURCE_CASE: 'Case执行',
    }

    @staticmethod
    def target_type_by_detail(detail: TestSuiteDetails | dict):
        detail_type = detail.get('type') if isinstance(detail, dict) else detail.type
        try:
            detail_type = int(detail_type)
        except (TypeError, ValueError):
            return 'unknown'
        if detail_type == TestCaseTypeEnum.API.value:
            return ExecutionResultService.TARGET_API_CASE
        if detail_type == TestCaseTypeEnum.UI.value:
            return ExecutionResultService.TARGET_UI_CASE
        if detail_type == TestCaseTypeEnum.PYTEST.value:
            return ExecutionResultService.TARGET_PYTEST_CASE
        return 'unknown'

    @classmethod
    def save_result(
            cls,
            detail: TestSuiteDetails,
            result_data: Any,
            source_snapshot: dict | None = None,
            prepared_result_payload: dict | None = None,
    ):
        result_data = cls.normalize_detail_result_data(detail, result_data)
        summary_data = cls.build_summary_data(detail, result_data)
        summary_meta = cls.extract_api_snapshot_meta(result_data)
        return cls._save_result_and_summary(
            detail, result_data, summary_data, summary_meta,
            source_snapshot=source_snapshot, prepared_result_payload=prepared_result_payload,
        )

    @classmethod
    def save_snapshot(cls, detail: TestSuiteDetails, snapshot_data: dict[str, Any]):
        normalized_steps = cls.normalize_detail_result_data(detail, snapshot_data)
        summary_data = cls.build_summary_data(detail, normalized_steps)
        summary_meta = cls.extract_api_snapshot_meta(snapshot_data)
        return cls._save_result_and_summary(detail, snapshot_data, summary_data, summary_meta)

    @classmethod
    def _save_result_and_summary(
            cls, detail, result_data, summary_data, summary_meta, *,
            source_snapshot=None, prepared_result_payload=None,
    ):
        prepared = prepared_result_payload
        if prepared is None:
            prepared = ExecutionResultService.prepare_result_payload(
                result_data, cls.target_type_by_detail(detail), detail.case_id, detail.test_suite_id, detail.id,
            )

        def persist():
            result = cls.create_latest_result(
                detail, result_data, source_snapshot=source_snapshot,
                prepared_result_payload=prepared,
            )
            cls.save_detail_summary(detail, summary_data, summary_meta)
            return result

        return ExecutionResultService.run_write_transaction(persist)

    @classmethod
    def create_latest_result(
            cls,
            detail: TestSuiteDetails,
            result_data: Any,
            source_snapshot: dict | None = None,
            prepared_result_payload: dict | None = None,
    ) -> ExecutionResult:
        return ExecutionResultService.save_result(
            source_type=ExecutionResultService.SOURCE_REPORT,
            target_type=cls.target_type_by_detail(detail),
            target_id=detail.case_id,
            result_data=result_data,
            test_env=detail.test_env,
            revision_id=detail.api_case_revision_id,
            release_id=detail.api_case_release_id,
            test_suite_id=detail.test_suite_id,
            test_suite_detail_id=detail.id,
            status=detail.status,
            error_message=detail.error_message,
            source_snapshot=source_snapshot,
            prepared_result_payload=prepared_result_payload,
        )

    @classmethod
    def get_result_data(cls, detail: TestSuiteDetails):
        summary_data = getattr(detail, 'summary_data', None)
        if summary_data is not None:
            children, meta = cls.unpack_summary_data(summary_data)
            if isinstance(meta, dict) and meta.get('summary_status') == 'skipped':
                return {
                    '__summary_skipped__': True,
                    'children': children,
                    'meta': meta,
                }
            if children is not None:
                return children
        payload = cls.get_latest_payload_by_detail_id(detail.id)
        if payload:
            payload_result_data = ExecutionResultService.load_result_data(payload)
            if payload_result_data is not None:
                return cls.normalize_detail_result_data(detail, payload_result_data)
        return None

    @classmethod
    def normalize_detail_result_data(cls, detail: TestSuiteDetails | dict, result_data: Any):
        detail_type = detail.get('type') if isinstance(detail, dict) else detail.type
        if detail_type == TestCaseTypeEnum.API.value:
            if cls.is_api_snapshot(result_data):
                return cls.only_last_api_retry_results(result_data.get('steps') or [])
            return cls.only_last_api_retry_results(result_data)
        return result_data

    @staticmethod
    def is_api_snapshot(result_data: Any):
        return isinstance(result_data, dict) and result_data.get('result_mode') == 'snapshot'

    @classmethod
    def extract_api_snapshot_meta(cls, result_data: Any):
        if not cls.is_api_snapshot(result_data):
            return None
        return {
            'result_mode': result_data.get('result_mode'),
            'snapshot_status': result_data.get('status'),
            'snapshot_reason': result_data.get('reason'),
            'snapshot_elapsed': result_data.get('elapsed'),
            'snapshot_progress': result_data.get('progress') or {},
            'snapshot_retry': result_data.get('retry') or {},
            'snapshot_current_step': result_data.get('current_step') or {},
            'snapshot_updated_at': result_data.get('updated_at'),
        }

    @classmethod
    def only_last_api_retry_results(cls, result_data: Any):
        if not isinstance(result_data, list):
            return result_data
        result_map = {}
        order = []
        for item in result_data:
            if not isinstance(item, dict):
                continue
            key = cls.api_result_unique_key(item)
            if key not in result_map:
                order.append(key)
            result_map[key] = item
        return [result_map[key] for key in order]

    @staticmethod
    def api_result_unique_key(item: dict):
        parameter_id = item.get('parameter_id')
        if parameter_id not in [None, '']:
            return 'parameter', str(parameter_id)
        return 'legacy', str(item.get('id')), str(item.get('name') or '')

    @classmethod
    def count_normalized_api_result(cls, detail: TestSuiteDetails):
        counter = {'success': 0, 'fail': 0, 'warning': 0}
        if detail.status in [
            TaskEnum.STAY_BEGIN.value,
            TaskEnum.PROCEED.value,
            TaskEnum.STOPPED.value,
        ]:
            return counter
        result_data = cls.get_result_data(detail)
        if isinstance(result_data, dict) and result_data.get('__summary_skipped__'):
            return cls.count_by_detail_fields(detail)
        if not result_data:
            counter['fail'] = detail.case_sum or 0
            return counter
        for item in result_data:
            if item.get('status') == StatusEnum.SUCCESS.value:
                counter['success'] += 1
            elif item.get('status') == TaskEnum.WARNING.value:
                counter['warning'] += 1
            else:
                counter['fail'] += 1
        result_sum = counter['success'] + counter['fail'] + counter['warning']
        counter['warning'] += max((detail.case_sum or 0) - result_sum, 0)
        return counter

    @staticmethod
    def count_by_detail_fields(detail: TestSuiteDetails):
        counter = {
            'success': detail.success or 0,
            'fail': detail.fail or 0,
            'warning': detail.warning or 0,
        }
        result_sum = counter['success'] + counter['fail'] + counter['warning']
        if result_sum > 0:
            return counter
        case_sum = detail.case_sum or 0
        if detail.status == StatusEnum.SUCCESS.value:
            counter['success'] = case_sum
        elif detail.status == TaskEnum.WARNING.value:
            counter['warning'] = case_sum
        elif detail.status == StatusEnum.FAIL.value:
            counter['fail'] = case_sum
        return counter

    @classmethod
    def normalized_api_counter(cls, details: list[TestSuiteDetails]):
        counter = {'success': 0, 'fail': 0, 'warning': 0}
        for detail in details:
            detail_counter = cls.count_normalized_api_result(detail)
            counter['success'] += detail_counter['success']
            counter['fail'] += detail_counter['fail']
            counter['warning'] += detail_counter['warning']
        return counter

    @classmethod
    def result_map(cls, detail_ids: list[int], defer_result_data: bool = False) -> dict[int, ExecutionResult]:
        if not detail_ids:
            return {}
        queryset = ExecutionResult.objects.filter(test_suite_detail_id__in=detail_ids).order_by()
        queryset = queryset.filter(is_latest=True)
        if defer_result_data:
            queryset = queryset.defer('result_data')
        return {
            item.test_suite_detail_id: item
            for item in queryset
        }

    @classmethod
    def attach_summary(cls, data_list: list[dict]):
        for item in data_list:
            result_data, snapshot_meta = cls.unpack_summary_data(item.get('summary_data'))
            timeout_termination = (
                snapshot_meta.get('termination')
                if isinstance(snapshot_meta, dict) and isinstance(snapshot_meta.get('termination'), dict)
                else None
            )
            if result_data is None and item.get('id') and not timeout_termination:
                payload = cls.get_payload_by_detail_id(item.get('id'))
                raw_result_data = ExecutionResultService.load_result_data(payload) if payload else None
                normalized_result = cls.normalize_detail_result_data(item, raw_result_data)
                result_data = cls.build_summary_data(item, normalized_result)
                snapshot_meta = cls.extract_api_snapshot_meta(raw_result_data)
                cls.save_detail_summary_by_id(item.get('id'), result_data, snapshot_meta)
            result_data = cls.ensure_api_warning_results(item, result_data, None, summary_only=True)
            item.pop('result_data', None)
            item.pop('summary_data', None)
            item['has_result_data'] = bool(result_data)
            item['children'] = result_data
            if snapshot_meta:
                item.update(snapshot_meta)
            cls.attach_case_type(item.get('children'), item['type'])
        return data_list

    @classmethod
    def attach_children(cls, data_list: list[dict], payload_map: dict[int, ExecutionResult] | None = None):
        detail_ids = [item['id'] for item in data_list if item.get('id')]
        payload_map = payload_map if payload_map is not None else cls.result_map(detail_ids)
        for item in data_list:
            payload = payload_map.get(item.get('id'))
            result_data = ExecutionResultService.load_result_data(payload) if payload else None
            snapshot_meta = cls.extract_api_snapshot_meta(result_data)
            result_data = cls.normalize_detail_result_data(item, result_data)
            result_data = cls.ensure_api_warning_results(item, result_data, payload)
            item.pop('result_data', None)
            item.pop('summary_data', None)
            item['result_size'] = payload.result_size if payload else cls.calc_result_size(result_data)
            item['has_result_data'] = bool(result_data)
            item['children'] = result_data
            if snapshot_meta:
                item.update(snapshot_meta)
            cls.attach_case_type(item.get('children'), item['type'])
        return data_list

    @staticmethod
    def attach_case_type(children: Any, case_type: int):
        """仅为结构化步骤补充用例类型，兼容历史字符串结果。"""
        if isinstance(children, dict):
            children['case_type'] = case_type
            return
        if not isinstance(children, list):
            return
        for child in children:
            if isinstance(child, dict):
                child['case_type'] = case_type

    @classmethod
    def get_payload_with_result_data(cls, payload_id: int):
        return ExecutionResult.objects.filter(id=payload_id).first()

    @classmethod
    def get_payload_by_detail_id(cls, detail_id: int):
        return cls.get_latest_payload_by_detail_id(detail_id)

    @classmethod
    def get_latest_payload_by_detail_id(cls, detail_id: int):
        return ExecutionResult.objects.filter(
            test_suite_detail_id=detail_id,
            is_latest=True,
        ).order_by('-attempt_no', '-id').first()

    @classmethod
    def get_payload_options(cls, detail_id: int, limit: int | None = None):
        detail = TestSuiteDetails.objects.filter(id=detail_id).only(
            'id',
            'type',
            'status',
            'case_id',
            'test_suite_id',
        ).first()
        if not detail:
            return []
        limit = cls.normalize_case_history_limit(limit)
        target_type = cls.target_type_by_detail(detail)
        queryset = ExecutionResult.objects.filter(
            target_type=target_type,
            target_id=detail.case_id,
        ).select_related('trigger_user')
        case_latest_id = queryset.order_by('-create_time', '-id').values_list('id', flat=True).first()
        ordered_items = []
        groups = [
            queryset.filter(test_suite_detail_id=detail.id),
            queryset.filter(test_suite_id=detail.test_suite_id).exclude(test_suite_detail_id=detail.id),
            queryset.exclude(test_suite_id=detail.test_suite_id),
        ]
        for group in groups:
            remaining = limit - len(ordered_items)
            if remaining <= 0:
                break
            ordered_items.extend(group.order_by('-create_time', '-id')[:remaining])
        data = []
        for item in ordered_items:
            status_text = TaskEnum.obj().get(item.status)
            if status_text is None and item.test_suite_detail_id == detail.id and item.is_latest:
                status_text = TaskEnum.obj().get(detail.status)
            source_scope = cls.payload_history_source(detail, item)
            data.append({
                'id': item.id,
                'attempt_no': item.attempt_no,
                'is_latest': item.is_latest,
                'is_case_latest': item.id == case_latest_id,
                'result_size': item.result_size,
                'create_time': item.create_time.strftime('%Y-%m-%d %H:%M:%S') if item.create_time else None,
                'update_time': item.update_time.strftime('%Y-%m-%d %H:%M:%S') if item.update_time else None,
                'status_text': status_text,
                'label': cls.payload_option_label(item, status_text),
                'source_scope': source_scope,
                'source_scope_name': cls.HISTORY_SOURCE_NAMES[source_scope],
                'source_type': item.source_type,
                'source_type_name': ExecutionResultService.SOURCE_TYPE_NAMES.get(
                    item.source_type,
                    item.source_type or '-',
                ),
                'test_suite_id': item.test_suite_id,
                'test_suite_detail_id': item.test_suite_detail_id,
                'trigger_user_name': item.trigger_user.name if item.trigger_user else None,
            })
        return data

    @classmethod
    def payload_matches_detail(cls, detail: TestSuiteDetails, payload: ExecutionResult | None) -> bool:
        return bool(
            payload
            and payload.target_type == cls.target_type_by_detail(detail)
            and payload.target_id == detail.case_id
        )

    @classmethod
    def payload_history_source(cls, detail: TestSuiteDetails, payload: ExecutionResult) -> str:
        if payload.test_suite_id == detail.test_suite_id:
            return cls.HISTORY_SOURCE_CURRENT_REPORT
        if payload.test_suite_id:
            return cls.HISTORY_SOURCE_OTHER_REPORT
        return cls.HISTORY_SOURCE_CASE

    @classmethod
    def normalize_case_history_limit(cls, value: int | None) -> int:
        try:
            value = int(value or cls.DEFAULT_CASE_HISTORY_LIMIT)
        except (TypeError, ValueError):
            return cls.DEFAULT_CASE_HISTORY_LIMIT
        return max(1, min(value, 100))

    @classmethod
    def payload_option_label(cls, payload: ExecutionResult, status_text: str | None = None):
        prefix = '最新，' if payload.is_latest else ''
        if payload.attempt_no <= 1:
            attempt_text = '首次执行'
        else:
            attempt_text = f'第{payload.attempt_no - 1}次重试'
        time_text = payload.update_time.strftime('%Y-%m-%d %H:%M:%S') if payload.update_time else '-'
        status_part = f'  {status_text}' if status_text else ''
        return f'{prefix}{attempt_text}{status_part}  {time_text}'

    @classmethod
    def payload_option_status_text(cls, detail: TestSuiteDetails, payload: ExecutionResult):
        result_data = cls.normalize_detail_result_data(detail, ExecutionResultService.load_result_data(payload))
        status_values = cls.collect_payload_statuses(result_data)
        if not status_values:
            return TaskEnum.obj().get(detail.status) if payload.is_latest else None
        if any(item in [TaskEnum.FAIL.value, 'failed', 'broken'] for item in status_values):
            return TaskEnum.obj().get(TaskEnum.FAIL.value)
        if any(item in [TaskEnum.WARNING.value, 'skipped'] for item in status_values):
            return TaskEnum.obj().get(TaskEnum.WARNING.value)
        if any(item == TaskEnum.PROCEED.value for item in status_values):
            return TaskEnum.obj().get(TaskEnum.PROCEED.value)
        if any(item == TaskEnum.STAY_BEGIN.value for item in status_values):
            return TaskEnum.obj().get(TaskEnum.STAY_BEGIN.value)
        if all(item in [TaskEnum.SUCCESS.value, 'passed'] for item in status_values):
            return TaskEnum.obj().get(TaskEnum.SUCCESS.value)
        return TaskEnum.obj().get(detail.status) if payload.is_latest else None

    @classmethod
    def collect_payload_statuses(cls, result_data: Any):
        if isinstance(result_data, list):
            status_values = []
            for item in result_data:
                if isinstance(item, dict) and item.get('status') not in [None, '']:
                    status_values.append(item.get('status'))
            return status_values
        if isinstance(result_data, dict) and result_data.get('status') not in [None, '']:
            return [result_data.get('status')]
        return []

    @classmethod
    def pack_summary_data(cls, children: Any, meta: dict | None = None):
        return {
            'children': children,
            'meta': meta or {},
        }

    @classmethod
    def unpack_summary_data(cls, summary_data: Any):
        if summary_data is None:
            return None, None
        if isinstance(summary_data, dict) and 'children' in summary_data:
            return summary_data.get('children'), summary_data.get('meta') or None
        return summary_data, None

    @classmethod
    def save_detail_summary(cls, detail: TestSuiteDetails, summary_data: Any, summary_meta: dict | None = None):
        detail.summary_data = cls.pack_summary_data(summary_data, summary_meta)
        detail.save(update_fields=['summary_data', 'update_time'])

    @classmethod
    def save_detail_summary_by_id(cls, detail_id: int, summary_data: Any, summary_meta: dict | None = None):
        TestSuiteDetails.objects.filter(id=detail_id).update(
            summary_data=cls.pack_summary_data(summary_data, summary_meta),
            update_time=timezone.now(),
        )

    @classmethod
    def build_summary_data(cls, detail: TestSuiteDetails | dict, result_data: Any):
        detail_type = detail.get('type') if isinstance(detail, dict) else detail.type
        if detail_type == TestCaseTypeEnum.API.value:
            return cls.build_api_summary(result_data)
        if detail_type == TestCaseTypeEnum.UI.value:
            return cls.build_ui_summary(result_data)
        if detail_type == TestCaseTypeEnum.PYTEST.value:
            return cls.build_pytest_summary(result_data)
        return cls.strip_large_value(result_data)

    @classmethod
    def build_api_summary(cls, result_data: Any):
        if not isinstance(result_data, list):
            return cls.strip_large_value(result_data)
        return [cls.build_api_step_summary(item) for item in result_data if isinstance(item, dict)]

    @classmethod
    def build_api_step_summary(cls, item: dict):
        response = item.get('response') or {}
        summary = cls.copy_keys(
            item,
            [
                'id',
                'parameter_id',
                'retry_index',
                'is_recovery',
                'main_status',
                'recovery_status',
                'recovery_errors',
                'name',
                'status',
                'error_message',
                'test_time',
                'api_info_id',
                'api_info_name',
            ],
        )
        summary['response_time'] = response.get('time')
        return summary

    @classmethod
    def build_assert_summary(cls, assertion: Any):
        if not isinstance(assertion, dict):
            return assertion
        return cls.copy_keys(assertion, ['name', 'status', 'error_message', 'msg', 'message'])

    @classmethod
    def build_ui_summary(cls, result_data: Any):
        if not isinstance(result_data, list):
            return cls.strip_large_value(result_data)
        return [cls.build_ui_step_summary(item) for item in result_data if isinstance(item, dict)]

    @classmethod
    def build_ui_step_summary(cls, item: dict):
        summary = cls.copy_keys(
            item,
            [
                'workspace_id',
                'id',
                'name',
                'type',
                'case_step_details_id',
                'test_time',
                'stop_time',
                'test_object',
                'is_auth_step',
                'is_final',
                'status',
                'error_message',
            ],
        )
        return summary

    @classmethod
    def build_ui_element_summary(cls, item: dict):
        return cls.copy_keys(
            item,
            [
                'id',
                'name',
                'type',
                'ope_key',
                'status',
                'error_message',
                'ass_msg',
                'test_time',
                'stop_time',
                'picture_path',
                'loc',
                'exp',
                'sub',
                'ele_quantity',
                'element_text',
                'ele_name',
            ],
        )

    @classmethod
    def build_pytest_summary(cls, result_data: Any):
        if isinstance(result_data, list):
            return [cls.build_pytest_item_summary(item) for item in result_data if isinstance(item, dict)]
        if isinstance(result_data, dict):
            return cls.build_pytest_item_summary(result_data)
        return result_data

    @classmethod
    def build_pytest_item_summary(cls, item: dict):
        summary = cls.copy_keys(
            item,
            [
                'id',
                'uuid',
                'name',
                'fullName',
                'nodeid',
                'status',
                'start',
                'stop',
            ],
        )
        status_details = item.get('statusDetails') or {}
        if isinstance(status_details, dict):
            summary['error_message'] = status_details.get('message') or status_details.get('trace')
            summary['statusDetails'] = cls.copy_keys(status_details, ['message'])
        else:
            summary['error_message'] = item.get('error_message')
        return summary

    @classmethod
    def build_pytest_attachment_summary(cls, item: dict):
        source = item.get('source')
        summary = cls.copy_keys(item, ['name', 'type'])
        summary['source_size'] = cls.calc_result_size(source)
        if cls.is_light_pytest_attachment(item):
            summary['source'] = cls.truncate_text(source)
        return summary

    @staticmethod
    def is_light_pytest_attachment(item: dict):
        name = item.get('name')
        source = item.get('source')
        if not isinstance(source, str):
            return False
        if name in ['请求URL', '请求方法', 'HTTP状态码', '响应时长(ms)']:
            return True
        return len(source) <= 2000

    @classmethod
    def strip_large_value(cls, value: Any):
        if isinstance(value, list):
            return [cls.strip_large_value(item) for item in value]
        if isinstance(value, dict):
            return {key: cls.strip_large_value(item) for key, item in value.items() if
                    key not in cls.large_result_keys()}
        if isinstance(value, str):
            return cls.truncate_text(value)
        return value

    @staticmethod
    def large_result_keys():
        return {
            'response',
            'request',
            'cache_data',
            'data_factory_cache_data',
            'attachments',
            'element_result_list',
            'children',
            'source',
            'json',
            'text',
            'headers',
            'request_body',
            'request_headers',
            'request_params',
            'request_file',
            'sse_events',
        }

    @staticmethod
    def truncate_text(value: Any, limit: int = 2000):
        if not isinstance(value, str):
            return value
        if len(value) <= limit:
            return value
        return f'{value[:limit]}...（已截断，完整内容请查看详细报告）'

    @staticmethod
    def copy_keys(data: dict, keys: list[str]):
        return {key: data.get(key) for key in keys if key in data}

    @classmethod
    def ensure_api_warning_results(
            cls,
            detail: dict,
            result_data: Any,
            payload: ExecutionResult | None,
            summary_only: bool = False,
    ):
        if detail.get('type') != TestCaseTypeEnum.API.value:
            return result_data
        if (detail.get('warning') or 0) <= 0:
            return result_data
        if not isinstance(result_data, list):
            result_data = []
        case_sum = detail.get('case_sum') or 0
        if len(result_data) >= case_sum:
            return result_data
        fixed_result_data = cls.build_missing_api_warning_results(detail, result_data)
        if len(fixed_result_data) == len(result_data):
            return result_data
        test_suite_detail_id = detail.get('id')
        if not test_suite_detail_id:
            return fixed_result_data
        result_size = cls.calc_result_size(fixed_result_data)
        if payload:
            if not summary_only:
                cls.update_payload_result_data(payload, fixed_result_data, result_size)
                summary_data = cls.build_summary_data(detail, fixed_result_data)
                cls.save_detail_summary_by_id(
                    test_suite_detail_id,
                    summary_data,
                    cls.extract_api_snapshot_meta(fixed_result_data),
                )
        else:
            summary_data = cls.build_summary_data(detail, fixed_result_data)
            cls.save_detail_summary_by_id(
                test_suite_detail_id,
                summary_data,
                cls.extract_api_snapshot_meta(fixed_result_data),
            )
        return fixed_result_data

    @classmethod
    def build_missing_api_warning_results(cls, detail: dict, result_data: list[dict]):
        case_id = detail.get('case_id')
        if not case_id:
            return result_data
        parameters = ApiCaseDetailedParameter.objects.filter(
            case_detailed__case_id=case_id,
        ).select_related(
            'case_detailed',
            'case_detailed__api_info',
        ).order_by(
            'case_detailed__case_sort',
            'case_detailed_id',
            'id',
        )
        executed_count_map = cls.api_result_count_by_case_detailed(result_data)
        fixed_result_data = list(result_data)
        for parameter in parameters:
            case_detailed = parameter.case_detailed
            executed_count = executed_count_map.get(case_detailed.id, 0)
            if executed_count > 0:
                executed_count_map[case_detailed.id] = executed_count - 1
                continue
            fixed_result_data.append(cls.build_api_warning_result(parameter))
        return fixed_result_data

    @staticmethod
    def api_result_count_by_case_detailed(result_data: list[dict]) -> dict[int, int]:
        count_map = {}
        for item in result_data:
            try:
                case_detailed_id = int(item.get('id'))
            except (TypeError, ValueError):
                continue
            count_map[case_detailed_id] = count_map.get(case_detailed_id, 0) + 1
        return count_map

    @classmethod
    def build_api_warning_result(cls, parameter: ApiCaseDetailedParameter) -> dict:
        case_detailed = parameter.case_detailed
        api_info = ApiInfoRuntimeService.resolve_runtime(case_detailed.api_info_id, allow_draft=True)
        request_model = ApiExecutionRequest(
            method=MethodEnum(api_info.method).name,
            url=api_info.url,
            headers={},
            params=parameter.params,
            protocol_type=api_info.protocol_type,
            body_type=api_info.body_type,
            body_config=parameter.body_config,
            sse_config=parameter.sse_config,
            posterior_file=None,
        )
        result_model = ApiCaseStepResult(
            id=case_detailed.id,
            parameter_id=parameter.id,
            api_info_id=api_info.id,
            api_info_name=api_info.name,
            name=parameter.name or api_info.name or f'场景ID:{case_detailed.id}',
            status=TaskEnum.WARNING.value,
            request=request_model,
            cache_data={},
            test_time=timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            error_message=cls.SKIP_MESSAGE,
        )
        return result_model.model_dump()

    @classmethod
    def clear_result(cls, detail_ids: list[int]):
        if not detail_ids:
            return 0
        return ExecutionResultService.clear_result_by_detail_ids(detail_ids)

    @classmethod
    def clean_expired_results(cls, retention_days: int | None = None) -> int:
        return ExecutionResultService.clear_expired_result_data(retention_days)

    @classmethod
    def update_payload_result_data(cls, payload: ExecutionResult, result_data: Any, result_size: int | None = None):
        if payload.result_object_key:
            try:
                default_storage.delete(payload.result_object_key)
            except Exception:
                log.system.exception('替换执行结果时旧文件删除失败，等待定时清理')
        result_payload = ExecutionResultService.prepare_result_payload(
            result_data,
            target_type=payload.target_type,
            target_id=payload.target_id,
            test_suite_id=payload.test_suite_id,
            test_suite_detail_id=payload.test_suite_detail_id,
        )
        payload.result_data = result_payload['result_data']
        payload.result_object_key = result_payload['result_object_key']
        payload.result_file_name = result_payload['result_file_name']
        payload.result_size = result_size if result_size is not None else result_payload['result_size']
        payload.result_checksum = result_payload['result_checksum']
        payload.result_cleaned = False
        payload.result_cleaned_at = None
        payload.save(update_fields=[
            'result_data',
            'result_object_key',
            'result_file_name',
            'result_size',
            'result_checksum',
            'result_cleaned',
            'result_cleaned_at',
            'update_time',
        ])

    @staticmethod
    def calc_result_size(result_data: Any) -> int:
        if result_data is None:
            return 0
        return len(
            json.dumps(
                result_data,
                ensure_ascii=False,
                default=str,
                separators=(',', ':'),
            ).encode('utf-8')
        )
