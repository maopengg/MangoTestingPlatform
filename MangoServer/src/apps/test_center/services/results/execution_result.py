import hashlib
import json
import posixpath
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import OperationalError, transaction
from django.db.models import BooleanField, Case, Q, Sum, Value, When
from django.utils import timezone
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import ExecutionResult, TestSuite, TestSuiteDetails
from src.apps.test_center.selectors.execution_result import ExecutionResultAccessSelector
from src.common.logging import log
from src.common.storage import build_public_file_url, delete_current_storage_file, iter_current_storage_files


class ExecutionResultService:
    SOURCE_PAGE = 'page'
    SOURCE_MCP = 'mcp'
    SOURCE_REPORT = 'report'
    SOURCE_RETRY = 'retry'
    TARGET_API_INFO = 'api_info'
    TARGET_API_CASE = 'api_case'
    TARGET_UI_PAGE_STEP = 'ui_page_step'
    TARGET_UI_CASE = 'ui_case'
    TARGET_PYTEST_CASE = 'pytest_case'
    SOURCE_TYPE_NAMES = {
        SOURCE_PAGE: '页面执行',
        SOURCE_MCP: 'MCP执行',
        SOURCE_REPORT: '测试报告',
        SOURCE_RETRY: '重试执行',
    }
    TARGET_TYPE_NAMES = {
        TARGET_API_INFO: 'API接口',
        TARGET_API_CASE: 'API用例',
        TARGET_UI_PAGE_STEP: 'UI页面步骤',
        TARGET_UI_CASE: 'UI用例',
        TARGET_PYTEST_CASE: 'Pytest用例',
    }

    @classmethod
    def save_result(
            cls,
            *,
            source_type: str,
            target_type: str,
            target_id: int,
            result_data: Any,
            test_env: int | None = None,
            revision_id: int | None = None,
            release_id: int | None = None,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
            status: int | None = None,
            error_message: str | None = None,
            duration: float | None = None,
            trigger_user_id: int | None = None,
            trace_id: str | None = None,
            task_id: str | None = None,
            source_snapshot: dict | None = None,
            prepared_result_payload: dict | None = None,
    ) -> ExecutionResult:
        status = cls.resolve_status(result_data, status)
        error_message = error_message or cls.resolve_error_message(result_data)
        duration = duration if duration is not None else cls.resolve_duration(result_data)
        result_payload = prepared_result_payload
        if result_payload is None:
            result_payload = cls.prepare_result_payload(
                result_data, target_type, target_id, test_suite_id, test_suite_detail_id,
            )
        latest_filter = cls.latest_filter(
            source_type=source_type,
            target_type=target_type,
            target_id=target_id,
            test_env=test_env,
            revision_id=revision_id,
            release_id=release_id,
            test_suite_detail_id=test_suite_detail_id,
        )
        fields = dict(
            source_type=source_type,
            target_type=target_type,
            target_id=target_id,
            test_suite_id=test_suite_id,
            test_suite_detail_id=test_suite_detail_id,
            revision_id=revision_id,
            release_id=release_id,
            test_env=test_env,
            status=status,
            error_message=error_message,
            duration=duration,
            is_latest=True,
            result_data=result_payload['result_data'],
            result_object_key=result_payload['result_object_key'],
            result_file_name=result_payload['result_file_name'],
            result_size=result_payload['result_size'],
            result_checksum=result_payload['result_checksum'],
            result_cleaned=False,
            trigger_user_id=trigger_user_id,
            trace_id=trace_id,
            task_id=task_id,
            source_snapshot=source_snapshot,
        )
        return cls.run_write_transaction(lambda: cls._save_result_record(fields, latest_filter))

    @staticmethod
    def run_write_transaction(operation):
        # 外层已有事务时由调用者整体重试，不能在已失效的事务内局部重试。
        nested = transaction.get_connection().in_atomic_block
        if nested:
            return operation()
        delays = (0.1, 0.3)
        for attempt in range(len(delays) + 1):
            try:
                with transaction.atomic():
                    return operation()
            except OperationalError as error:
                if not error.args or error.args[0] not in (1205, 1213) or attempt == len(delays):
                    raise
                log.system.warning(f'执行结果落库遇到锁冲突，回滚后重试：attempt={attempt + 1}')
                time.sleep(delays[attempt])

    @classmethod
    def _save_result_record(cls, fields: dict, latest_filter: dict) -> ExecutionResult:
        suite_id = fields['test_suite_id']
        detail_id = fields['test_suite_detail_id']
        if detail_id and suite_id is None:
            suite_id = TestSuiteDetails.objects.values_list('test_suite_id', flat=True).get(id=detail_id)
        # 与停止、清理及结果回调保持相同锁顺序，也覆盖首条结果尚不存在的情况。
        if suite_id is not None:
            TestSuite.objects.select_for_update().get(id=suite_id)
        if detail_id is not None:
            TestSuiteDetails.objects.select_for_update().get(id=detail_id, test_suite_id=suite_id)
        ExecutionResult.objects.filter(**latest_filter, is_latest=True).update(is_latest=False)
        latest_attempt_no = ExecutionResult.objects.filter(**latest_filter).order_by(
            '-attempt_no',
        ).values_list('attempt_no', flat=True).first()
        execution_result = ExecutionResult.objects.create(**fields, attempt_no=(latest_attempt_no or 0) + 1)
        if fields['target_type'] == cls.TARGET_API_CASE:
            from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService

            ModuleCoverageService.sync_api_case_execution_result(
                fields['target_id'],
                fields['status'],
                fields['revision_id'],
            )
        return execution_result

    @classmethod
    def prepare_result_payload(
            cls,
            result_data: Any,
            target_type: str,
            target_id: int,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
    ) -> dict:
        result_size = cls.calc_result_size(result_data)
        result_checksum = cls.calc_result_checksum(result_data)
        if not getattr(settings, 'RESULT_DATA_TO_FILE', True) or result_data is None:
            return {
                'result_data': result_data,
                'result_object_key': None,
                'result_file_name': None,
                'result_size': result_size,
                'result_checksum': result_checksum,
            }
        object_key, file_name = cls.save_result_file(
            result_data,
            target_type=target_type,
            target_id=target_id,
            test_suite_id=test_suite_id,
            test_suite_detail_id=test_suite_detail_id,
        )
        return {
            'result_data': None,
            'result_object_key': object_key,
            'result_file_name': file_name,
            'result_size': result_size,
            'result_checksum': result_checksum,
        }

    @classmethod
    def save_result_file(
            cls,
            result_data: Any,
            *,
            target_type: str,
            target_id: int,
            test_suite_id: int | None = None,
            test_suite_detail_id: int | None = None,
    ) -> tuple[str, str]:
        now = timezone.now()
        prefix = str(getattr(settings, 'RESULT_DATA_FILE_PREFIX', 'result') or 'result').strip('/\\') or 'result'
        scope = f'{target_type}_{target_id}'
        if test_suite_id and test_suite_detail_id:
            scope = f'report_{test_suite_id}/detail_{test_suite_detail_id}'
        file_name = f'{uuid.uuid4().hex}.json'
        object_key = posixpath.join(
            prefix,
            now.strftime('%Y/%m/%d'),
            scope,
            file_name,
        )
        payload = json.dumps(result_data, ensure_ascii=False, default=str, separators=(',', ':')).encode('utf-8')
        saved_name = default_storage.save(object_key, ContentFile(payload))
        return saved_name.replace('\\', '/'), file_name

    @staticmethod
    def latest_filter(
            *,
            source_type: str,
            target_type: str,
            target_id: int,
            test_env: int | None = None,
            revision_id: int | None = None,
            release_id: int | None = None,
            test_suite_detail_id: int | None = None,
    ) -> dict:
        if test_suite_detail_id:
            return {
                'test_suite_detail_id': test_suite_detail_id,
            }
        return {
            'source_type': source_type,
            'target_type': target_type,
            'target_id': target_id,
            'test_env': test_env,
            'revision_id': revision_id,
            'release_id': release_id,
            'test_suite_detail_id__isnull': True,
        }

    @classmethod
    def result_options(cls, filters: dict, page: int = 1, page_size: int = 20, *, queryset=None) -> tuple[
        list[dict], int]:
        queryset = cls.summary_queryset() if queryset is None else queryset
        queryset = queryset.filter(**filters)
        total = queryset.count()
        start = max(page - 1, 0) * page_size
        data = [cls.serialize_summary(item) for item in queryset[start:start + page_size]]
        return data, total

    @classmethod
    def summary_queryset(cls):
        return ExecutionResult.objects.select_related('trigger_user').annotate(
            has_inline_result_data=Case(
                When(result_data__isnull=False, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).defer('result_data').order_by('-create_time', '-id')

    @classmethod
    def visible_results(cls, user):
        from src.apps.auto_api.selectors.querysets import ApiQuerySelector
        from src.apps.auto_ui.selectors.querysets import UiQuerySelector
        from src.apps.auto_pytest.selectors.querysets import PytestQuerySelector

        target_access = {
            cls.TARGET_API_INFO: ({'api.info:read', 'api.info:change', 'api.info:change'},
                                  ApiQuerySelector.api_info(), 'project_product_id'),
            cls.TARGET_API_CASE: ({'api.case:read', 'api.case:change', 'api.case:change'},
                                  ApiQuerySelector.api_case(), 'project_product_id'),
            cls.TARGET_UI_PAGE_STEP: ({'ui.page_steps:read', 'ui.page_steps:change'},
                                      UiQuerySelector.page_steps(), 'project_product_id'),
            cls.TARGET_UI_CASE: ({'ui.case:read', 'ui.case:change', 'ui.case:change'},
                                 UiQuerySelector.ui_case(), 'project_product_id'),
            cls.TARGET_PYTEST_CASE: ({'pytest.case:read', 'pytest.case:change'},
                                     PytestQuerySelector.pytest_case(), 'project_product__project_product_id'),
        }
        return ExecutionResultAccessSelector.visible_queryset(cls.summary_queryset(), user, target_access)

    @classmethod
    def admin_result_options(
            cls,
            filters: dict,
            page: int = 1,
            page_size: int = 20,
    ) -> tuple[list[dict], int]:
        queryset = cls.summary_queryset()
        filters = dict(filters)
        result_state = filters.pop('result_state', None)
        result_states = filters.pop('result_state__in', None)
        if result_state == 'available':
            queryset = queryset.filter(cls.result_payload_filter(), result_cleaned=False)
        elif result_state == 'cleaned':
            queryset = queryset.filter(result_cleaned=True)
        elif result_state == 'empty':
            queryset = queryset.filter(
                result_data__isnull=True,
                result_object_key__isnull=True,
                result_cleaned=False,
            )
        elif result_states:
            state_filter = Q()
            if 'available' in result_states:
                state_filter |= cls.result_payload_filter() & Q(result_cleaned=False)
            if 'cleaned' in result_states:
                state_filter |= Q(result_cleaned=True)
            if 'empty' in result_states:
                state_filter |= Q(
                    result_data__isnull=True,
                    result_object_key__isnull=True,
                    result_cleaned=False,
                )
            queryset = queryset.filter(state_filter)
        queryset = queryset.filter(**filters)
        total = queryset.count()
        start = max(page - 1, 0) * page_size
        data = [cls.serialize_summary(item) for item in queryset[start:start + page_size]]
        return data, total

    @classmethod
    def admin_config(cls) -> dict:
        retention_days = cls.retention_days()
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        display_cutoff_time = (
            timezone.localtime(cutoff_time)
            if timezone.is_aware(cutoff_time)
            else cutoff_time
        )
        payload_filter = cls.result_payload_filter()
        available_queryset = ExecutionResult.objects.filter(
            payload_filter,
            result_cleaned=False,
        )
        return {
            'retention_days': retention_days,
            'cutoff_time': display_cutoff_time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_count': ExecutionResult.objects.count(),
            'available_count': available_queryset.count(),
            'expired_pending_count': available_queryset.filter(
                create_time__lt=cutoff_time,
            ).count(),
            'cleaned_count': ExecutionResult.objects.filter(result_cleaned=True).count(),
            'available_result_size': available_queryset.aggregate(
                total=Sum('result_size'),
            )['total'] or 0,
            'source_type_options': [
                {'key': key, 'title': title}
                for key, title in cls.SOURCE_TYPE_NAMES.items()
            ],
            'target_type_options': [
                {'key': key, 'title': title}
                for key, title in cls.TARGET_TYPE_NAMES.items()
            ],
            'status_options': TaskEnum.get_option(),
            'test_env_options': EnvironmentEnum.get_option(),
            'result_state_options': [
                {'key': 'available', 'title': '结果可用'},
                {'key': 'cleaned', 'title': '已清理'},
                {'key': 'empty', 'title': '无完整结果'},
            ],
            'is_latest_options': [
                {'key': 'true', 'title': '最新结果'},
                {'key': 'false', 'title': '历史结果'},
            ],
        }

    @classmethod
    def result_detail(cls, result_id: int, *, queryset=None) -> dict | None:
        queryset = ExecutionResult.objects.all() if queryset is None else queryset
        item = queryset.filter(id=result_id).select_related('trigger_user').defer(None).first()
        return cls.serialize_detail(item) if item else None

    @staticmethod
    def open_result_file(result_id: int, *, queryset=None):
        queryset = ExecutionResult.objects.all() if queryset is None else queryset
        item = queryset.filter(id=result_id).select_related(None).only(
            'id',
            'result_object_key',
            'result_file_name',
            'result_cleaned',
        ).first()
        if (
                item is None or
                item.result_cleaned or
                not item.result_object_key
        ):
            return None, None
        try:
            return (
                default_storage.open(item.result_object_key, 'rb'),
                item.result_file_name or f'execution-result-{item.id}.json',
            )
        except Exception:
            return None, None

    @classmethod
    def latest_result_detail(cls, filters: dict, *, queryset=None) -> dict | None:
        queryset = ExecutionResult.objects.all() if queryset is None else queryset
        item = queryset.filter(**filters).select_related('trigger_user').defer(None).order_by(
            '-create_time',
            '-id',
        ).first()
        return cls.serialize_detail(item) if item else None

    @classmethod
    def latest_result_data(
            cls,
            *,
            target_type: str,
            target_id: int,
            revision_id: int | None = None,
            release_id: int | None = None,
            test_env: int | None = None,
            source_type: str | None = None,
    ) -> dict:
        filters = {
            'target_type': target_type,
            'target_id': target_id,
            'is_latest': True,
        }
        if revision_id is not None:
            filters['revision_id'] = revision_id
        if release_id is not None:
            filters['release_id'] = release_id
        if test_env is not None:
            filters['test_env'] = test_env
        if source_type:
            filters['source_type'] = source_type
        item = ExecutionResult.objects.filter(**filters).order_by('-create_time', '-id').first()
        result_data = cls.load_result_data(item)
        return result_data if isinstance(result_data, dict) else {}

    @classmethod
    def latest_api_case_parameter_result(
            cls,
            *,
            case_id: int,
            parameter_id: int,
            test_env: int | None = None,
            source_type: str | None = None,
    ) -> dict:
        filters = {
            'target_type': cls.TARGET_API_CASE,
            'target_id': case_id,
        }
        if test_env is not None:
            filters['test_env'] = test_env
        if source_type:
            filters['source_type'] = source_type
        for item in ExecutionResult.objects.filter(**filters).order_by('-create_time', '-id')[:20]:
            parameter_result = cls.find_api_case_parameter_result(cls.load_result_data(item), parameter_id)
            if parameter_result:
                return parameter_result
        return {}

    @staticmethod
    def find_api_case_parameter_result(result_data: Any, parameter_id: int) -> dict:
        if not isinstance(result_data, dict):
            return {}
        for step in result_data.get('steps') or []:
            if not isinstance(step, dict):
                continue
            if step.get('parameter_id') == parameter_id:
                return step
            for parameter in step.get('parameters') or []:
                if isinstance(parameter, dict) and parameter.get('id') == parameter_id:
                    return parameter.get('result_data') if isinstance(parameter.get('result_data'), dict) else parameter
        return {}

    @classmethod
    def serialize_summary(cls, item: ExecutionResult) -> dict:
        return {
            'id': item.id,
            'source_type': item.source_type,
            'source_type_name': cls.SOURCE_TYPE_NAMES.get(item.source_type, item.source_type or '-'),
            'target_type': item.target_type,
            'target_type_name': cls.TARGET_TYPE_NAMES.get(item.target_type, item.target_type or '-'),
            'target_id': item.target_id,
            'test_suite': item.test_suite_id,
            'test_suite_detail': item.test_suite_detail_id,
            'revision_id': item.revision_id,
            'release_id': item.release_id,
            'test_env': item.test_env,
            'test_env_name': EnvironmentEnum.obj().get(item.test_env, '-'),
            'status': item.status,
            'status_name': TaskEnum.obj().get(item.status, '-'),
            'error_message': item.error_message,
            'duration': item.duration,
            'attempt_no': item.attempt_no,
            'is_latest': item.is_latest,
            'result_size': item.result_size,
            'has_result_data': cls.has_result_data(item),
            'result_cleaned': item.result_cleaned,
            'trigger_user': item.trigger_user_id,
            'trigger_user_name': item.trigger_user.name if item.trigger_user else '-',
            'trace_id': item.trace_id,
            'task_id': item.task_id,
            'create_time': item.create_time.strftime('%Y-%m-%d %H:%M:%S') if item.create_time else None,
            'update_time': item.update_time.strftime('%Y-%m-%d %H:%M:%S') if item.update_time else None,
            'label': cls.result_label(item),
        }

    @classmethod
    def serialize_detail(cls, item: ExecutionResult) -> dict:
        data = cls.serialize_summary(item)
        if cls.should_return_download_url(item):
            data['result_data'] = None
            data['result_too_large'] = True
            data['download_url'] = cls.result_download_url(item)
        else:
            data['result_data'] = cls.load_result_data(item)
            data['result_too_large'] = False
            data['download_url'] = None
        if item.target_type == cls.TARGET_PYTEST_CASE:
            data['source_snapshot'] = item.source_snapshot
        return data

    @classmethod
    def serialize_run_response(cls, item: ExecutionResult) -> dict:
        return cls.serialize_summary(item)

    @classmethod
    def load_result_data(cls, item: ExecutionResult | None):
        if not item or item.result_cleaned:
            return None
        if item.result_data is not None:
            return item.result_data
        if not item.result_object_key:
            return None
        try:
            with default_storage.open(item.result_object_key, 'rb') as file:
                content = file.read()
        except Exception:
            return None
        if not content:
            return None
        try:
            return json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @classmethod
    def should_return_download_url(cls, item: ExecutionResult | None) -> bool:
        if not item or item.result_cleaned or not item.result_object_key:
            return False
        inline_max_size = int(getattr(settings, 'RESULT_DATA_DETAIL_INLINE_MAX_SIZE', 5 * 1024 * 1024) or 0)
        return inline_max_size > 0 and (item.result_size or 0) > inline_max_size

    @staticmethod
    def result_download_url(item: ExecutionResult | None) -> str | None:
        if not item or not item.result_object_key:
            return None
        try:
            return build_public_file_url(item.result_object_key)
        except Exception:
            return None

    @staticmethod
    def has_result_data(item: ExecutionResult) -> bool:
        has_inline_result_data = getattr(item, 'has_inline_result_data', None)
        if has_inline_result_data is None:
            has_inline_result_data = item.result_data is not None
        return bool(
            not item.result_cleaned
            and (has_inline_result_data or item.result_object_key)
        )

    @staticmethod
    def result_payload_filter() -> Q:
        return Q(result_data__isnull=False) | Q(result_object_key__isnull=False)

    @classmethod
    def result_label(cls, item: ExecutionResult) -> str:
        prefix = '最新，' if item.is_latest else ''
        attempt_text = '首次执行' if item.attempt_no <= 1 else f'第{item.attempt_no - 1}次重试'
        status_text = TaskEnum.obj().get(item.status)
        time_text = item.create_time.strftime('%Y-%m-%d %H:%M:%S') if item.create_time else '-'
        status_part = f'  {status_text}' if status_text else ''
        return f'{prefix}{attempt_text}{status_part}  {time_text}'

    @classmethod
    def resolve_status(cls, result_data: Any, status: int | None = None):
        if status is not None:
            return status
        if isinstance(result_data, dict):
            if result_data.get('status') is not None:
                return result_data.get('status')
            if result_data.get('error_msg') or result_data.get('error_message'):
                return StatusEnum.FAIL.value
            if result_data.get('code') is not None:
                return StatusEnum.SUCCESS.value
            # API 调试结果 wraps the actual response under ``response``.
            # Keep the execution status consistent for page/MCP runs so version
            # creation can recognize a successful editing-state debug run.
            response = result_data.get('response')
            if isinstance(response, dict):
                if response.get('error_msg') or response.get('error_message'):
                    return StatusEnum.FAIL.value
                if response.get('mcp_is_error') is True or response.get('mcp_protocol_error'):
                    return StatusEnum.FAIL.value
                if response.get('mcp_is_error') is False:
                    return StatusEnum.SUCCESS.value
                if response.get('code') is not None:
                    return StatusEnum.SUCCESS.value
        return None

    @staticmethod
    def resolve_error_message(result_data: Any):
        if not isinstance(result_data, dict):
            return None
        return result_data.get('error_message') or result_data.get('error_msg')

    @staticmethod
    def resolve_duration(result_data: Any):
        if not isinstance(result_data, dict):
            return None
        if result_data.get('time') is not None:
            return result_data.get('time')
        response = result_data.get('response')
        if isinstance(response, dict):
            return response.get('time')
        return None

    @staticmethod
    def calc_result_size(result_data: Any) -> int:
        if result_data is None:
            return 0
        return len(json.dumps(result_data, ensure_ascii=False, default=str, separators=(',', ':')).encode('utf-8'))

    @staticmethod
    def calc_result_checksum(result_data: Any) -> str | None:
        if result_data is None:
            return None
        payload = json.dumps(result_data, ensure_ascii=False, default=str, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    @classmethod
    def clear_result_by_detail_ids(cls, detail_ids: list[int]):
        if not detail_ids:
            return 0
        return ExecutionResult.objects.filter(
            test_suite_detail_id__in=detail_ids,
            is_latest=True,
        ).update(is_latest=False, update_time=timezone.now())

    @classmethod
    def clear_expired_result_data(cls, retention_days: int | None = None) -> int:
        retention_days = retention_days or cls.retention_days()
        cutoff_time = timezone.now() - timedelta(days=retention_days)
        queryset = ExecutionResult.objects.filter(
            cls.result_payload_filter(),
            create_time__lt=cutoff_time,
            result_cleaned=False,
        )
        updated = 0
        now = timezone.now()
        for item in queryset.distinct().iterator(chunk_size=200):
            if item.result_object_key:
                try:
                    default_storage.delete(item.result_object_key)
                except Exception:
                    log.system.exception(f'执行结果文件删除失败，保留待重试状态：result_id={item.id}')
                    continue
            item.result_data = None
            item.result_cleaned = True
            item.result_cleaned_at = now
            item.save(update_fields=['result_data', 'result_cleaned', 'result_cleaned_at', 'update_time'])
            updated += 1
        return updated

    @classmethod
    def cleanup_expired(cls, retention_days: int | None = None) -> dict:
        retention_days = retention_days or cls.retention_days()
        return {
            'retention_days': retention_days,
            'updated_count': cls.clear_expired_result_data(retention_days),
            **cls.cleanup_expired_storage_files(retention_days),
        }

    @classmethod
    def cleanup_expired_storage_files(cls, retention_days: int) -> dict:
        """回收已标记清理及无数据库引用的旧结果；不扫描其他环境。"""
        cutoff = timezone.now() - timedelta(days=retention_days)
        prefix = str(getattr(settings, 'RESULT_DATA_FILE_PREFIX', 'result') or 'result').strip('/\\')
        if not prefix or any(part in {'.', '..'} for part in prefix.split('/')):
            log.system.error('执行结果存储前缀无效，跳过历史文件清理')
            return {'deleted_file_count': 0, 'failed_file_count': 0, 'storage_scan_failed': True}
        # 仅清理平台生成的带日期、业务范围和 UUID 的 JSON 文件。
        pattern = re.compile(
            rf'^{re.escape(prefix)}/(\d{{4}}/\d{{2}}/\d{{2}})/'
            r'(?:report_\d+/detail_\d+|(?:api_info|api_case|ui_page_step|ui_case|pytest_case)_\d+)'
            r'/[0-9a-f]{32}\.json$'
        )
        deleted = failed = 0
        scan_failed = False
        root = str(getattr(settings, 'FILE_STORAGE_ROOT', '')).strip('/\\')
        try:
            for name, modified_at in iter_current_storage_files(prefix):
                relative = name[len(root) + 1:] if root and name.startswith(root + '/') else name
                match = pattern.fullmatch(relative)
                if not match or modified_at is None:
                    continue
                try:
                    file_date = datetime.strptime(match.group(1), '%Y/%m/%d').date()
                except ValueError:
                    continue
                modified_date = timezone.localtime(modified_at).date() if timezone.is_aware(modified_at) else modified_at.date()
                # 截止日整天保留，避免时区或历史记录回填导致提前删除。
                if file_date >= cutoff.date() or modified_date >= cutoff.date():
                    continue
                try:
                    delete_current_storage_file(name)
                    deleted += 1
                except Exception:
                    failed += 1
                    log.system.exception(f'历史执行结果文件删除失败，下次清理重试：path={name}')
        except Exception:
            scan_failed = True
            log.system.exception('历史执行结果文件扫描失败，下次清理重试')
        return {'deleted_file_count': deleted, 'failed_file_count': failed, 'storage_scan_failed': scan_failed}

    @staticmethod
    def retention_days() -> int:
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get_ranged_int('RESULT_DATA_RETENTION_DAYS')
