"""
7.1.0 API version data migration and recent report summary backfill.

Usage:
    cd MangoServer
    python version_migration_scripts/v_7_1_0_2026_07_22_api_version_data.py --env test --stage status
    python version_migration_scripts/v_7_1_0_2026_07_22_api_version_data.py --env test --stage all --execute
    python version_migration_scripts/v_7_1_0_2026_07_22_api_version_data.py --env test --stage report_summary --days 10 --execute

The default mode is dry-run. Add --execute to write data.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from typing import Any


TARGET_VERSION = '7.1.0'


def setup_django(env: str) -> None:
    os.environ['DJANGO_ENV'] = env
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')

    server_dir = Path(__file__).resolve().parents[1]
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    import django

    django.setup()


def build_preview(summary_data: Any) -> str:
    if summary_data is None:
        return 'summary=None'
    if isinstance(summary_data, list):
        first = summary_data[0] if summary_data else None
        first_keys = list(first.keys())[:12] if isinstance(first, dict) else []
        return f'summary=list[{len(summary_data)}], first_keys={first_keys}'
    if isinstance(summary_data, dict):
        return f'summary=dict, keys={list(summary_data.keys())[:12]}'
    return f'summary={type(summary_data).__name__}'


def normalize_limit(value: int) -> int:
    return max(1, min(int(value or 100), 500))


def run_with_retry(label, retry_times: int, retry_sleep: float, func):
    from django.db import DatabaseError, close_old_connections

    last_exc = None
    for index in range(retry_times + 1):
        try:
            close_old_connections()
            return func()
        except DatabaseError as exc:
            last_exc = exc
            close_old_connections()
            if index >= retry_times:
                break
            print(f'{label} 数据库异常，{retry_sleep}s 后重试 ({index + 1}/{retry_times})：{exc}', flush=True)
            if retry_sleep > 0:
                time.sleep(retry_sleep)
    raise last_exc


class MigrationRunner:
    def __init__(self, args):
        self.args = args
        self.limit = normalize_limit(args.limit)

        from django.conf import settings

        self.settings = settings
        self._assert_ready()

        from src.apps.auto_api.models import (
            ApiCase,
            ApiCaseDetailed,
            ApiCaseDetailedParameter,
            ApiCaseRelease,
            ApiCaseRevision,
            ApiHeaders,
            ApiInfo,
            ApiInfoRelease,
            ApiInfoRevision,
            ApiInfoGrpcConfig,
            ApiInfoHttpConfig,
            ApiInfoMcpBinding,
            ApiInfoMcpConfig,
            ApiInfoWebSocketConfig,
        )
        from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
        from src.apps.auto_api.schemas.models.version import ApiCaseRevisionPayloadModel
        from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
        from src.apps.auto_api.services.api_info.version import ApiInfoRevisionService
        from src.apps.system.enums import TaskCaseVersionPolicyEnum
        from src.apps.test_center.enums.case import TestCaseTypeEnum
        from src.apps.system.models import TasksDetails, ExecutionResult, TestSuiteDetails
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService

        self.ApiCase = ApiCase
        self.ApiCaseDetailed = ApiCaseDetailed
        self.ApiCaseDetailedParameter = ApiCaseDetailedParameter
        self.ApiCaseRelease = ApiCaseRelease
        self.ApiCaseRevision = ApiCaseRevision
        self.ApiHeaders = ApiHeaders
        self.ApiInfo = ApiInfo
        self.ApiInfoRelease = ApiInfoRelease
        self.ApiInfoRevision = ApiInfoRevision
        self.ApiInfoGrpcConfig = ApiInfoGrpcConfig
        self.ApiInfoHttpConfig = ApiInfoHttpConfig
        self.ApiInfoMcpBinding = ApiInfoMcpBinding
        self.ApiInfoMcpConfig = ApiInfoMcpConfig
        self.ApiInfoWebSocketConfig = ApiInfoWebSocketConfig
        self.ApiInfoRuntimeService = ApiInfoRuntimeService
        self.ApiCaseRevisionPayloadModel = ApiCaseRevisionPayloadModel
        self.ApiCaseRevisionService = ApiCaseRevisionService
        self.ApiInfoRevisionService = ApiInfoRevisionService
        self.TaskCaseVersionPolicyEnum = TaskCaseVersionPolicyEnum
        self.TestCaseTypeEnum = TestCaseTypeEnum
        self.TasksDetails = TasksDetails
        self.ExecutionResult = ExecutionResult
        self.TestSuiteDetails = TestSuiteDetails
        self.ExecutionResultService = ExecutionResultService
        self.TestSuiteExecutionResultService = TestSuiteExecutionResultService
        self._legacy_columns_cache = {}

    def _assert_ready(self):
        if self.settings.VERSION != TARGET_VERSION:
            raise RuntimeError(f'当前系统版本是 {self.settings.VERSION}，该脚本只允许在 {TARGET_VERSION} 执行')

    def _retry(self, label, func):
        return run_with_retry(label, self.args.retry_times, self.args.retry_sleep, func)

    def _published_api_info_ids(self):
        return self.ApiInfoRelease.objects.filter(
            is_current=True,
            status=self.ApiInfoRelease.STATUS_PUBLISHED,
        ).values('api_info_id')

    def _published_api_case_ids(self):
        return self.ApiCaseRelease.objects.filter(
            is_current=True,
            status=self.ApiCaseRelease.STATUS_PUBLISHED,
        ).values('api_case_id')

    def current_counts(self) -> dict[str, int]:
        return self._retry('统计迁移状态', lambda: {
            'api_info_total': self.ApiInfo.objects.count(),
            'api_info_release': self.ApiInfoRelease.objects.filter(
                is_current=True,
                status=self.ApiInfoRelease.STATUS_PUBLISHED,
            ).count(),
            'api_case_total': self.ApiCase.objects.count(),
            'api_case_release': self.ApiCaseRelease.objects.filter(
                is_current=True,
                status=self.ApiCaseRelease.STATUS_PUBLISHED,
            ).count(),
            'api_case_revision': self.ApiCaseRevision.objects.count(),
            'api_case_detailed_pinned': self.ApiCaseDetailed.objects.filter(
                pinned_api_info_revision_id__isnull=False,
            ).count(),
            'tasks_details_total': self.TasksDetails.objects.filter(api_case_id__isnull=False).count(),
            'tasks_details_bound': self.TasksDetails.objects.filter(api_case_revision_id__isnull=False).count(),
            'test_suite_details_total': self.TestSuiteDetails.objects.filter(
                type=self.TestCaseTypeEnum.API.value,
            ).count(),
            'test_suite_details_bound': self.TestSuiteDetails.objects.filter(
                type=self.TestCaseTypeEnum.API.value,
                api_case_revision_id__isnull=False,
            ).count(),
            'test_suite_details_summary': self.TestSuiteDetails.objects.filter(summary_data__isnull=False).count(),
        })

    def print_counts(self, prefix: str):
        counts = self.current_counts()
        print(
            f"{prefix} "
            f"api_info_release={counts['api_info_release']}/{counts['api_info_total']} "
            f"api_case_release={counts['api_case_release']}/{counts['api_case_total']} "
            f"api_case_revision={counts['api_case_revision']} "
            f"pinned_steps={counts['api_case_detailed_pinned']} "
            f"task_bound={counts['tasks_details_bound']}/{counts['tasks_details_total']} "
            f"report_detail_bound={counts['test_suite_details_bound']}/{counts['test_suite_details_total']} "
            f"report_summary={counts['test_suite_details_summary']}",
            flush=True,
        )
        return counts

    def _legacy_columns(self, table_name: str) -> set[str]:
        if table_name not in self._legacy_columns_cache:
            from django.db import connection

            with connection.cursor() as cursor:
                description = connection.introspection.get_table_description(cursor, table_name)
            self._legacy_columns_cache[table_name] = {column.name for column in description}
        return self._legacy_columns_cache[table_name]

    def _legacy_rows(self, table_name: str, ids: list[int], fields: tuple[str, ...]) -> dict[int, dict[str, Any]]:
        """Read deprecated columns without adding them back to the Django models."""
        from django.db import connection

        columns = self._legacy_columns(table_name)
        selected = ['id', *[field for field in fields if field in columns]]
        if not ids or len(selected) == 1:
            return {}
        quoted_table = connection.ops.quote_name(table_name)
        quoted_fields = ', '.join(connection.ops.quote_name(field) for field in selected)
        placeholders = ', '.join(['%s'] * len(ids))
        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT {quoted_fields} FROM {quoted_table} WHERE id IN ({placeholders})',
                ids,
            )
            rows = cursor.fetchall()
        return {row[0]: dict(zip(selected, row)) for row in rows}

    @staticmethod
    def _legacy_json(value):
        if value in (None, '', {}, []):
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (TypeError, ValueError):
                return value
        return value

    def _legacy_body_config(self, values: dict[str, Any]) -> tuple[str, dict | None]:
        from src.apps.auto_api.views.api_info import build_body_from_legacy

        existing_config = self._legacy_json(values.get('body_config'))
        existing_type = values.get('body_type') or ''
        if existing_config not in (None, '', {}, []):
            return existing_type or 'json', existing_config
        file_payload = self._legacy_json(values.get('file'))
        return build_body_from_legacy(
            data=self._legacy_json(values.get('data')),
            json_body=values.get('json'),
            file_payload=file_payload,
        )

    def backup_api_protocol_sources(self):
        backup_name = self.args.backup_table_name
        if not backup_name:
            raise RuntimeError('协议迁移备份阶段必须传入 --backup-table-name')
        if not re.fullmatch(r'[A-Za-z0-9_]+', backup_name):
            raise RuntimeError('--backup-table-name 只允许字母、数字和下划线')

        from django.db import connection

        source_tables = ('api_info', 'api_case_detailed', 'api_case_detailed_parameter')
        with connection.cursor() as cursor:
            for source_table in source_tables:
                target_table = f'{backup_name}_{source_table}'
                cursor.execute(
                    f'CREATE TABLE IF NOT EXISTS {connection.ops.quote_name(target_table)} '
                    f'LIKE {connection.ops.quote_name(source_table)}'
                )
                cursor.execute(f'DELETE FROM {connection.ops.quote_name(target_table)}')
                cursor.execute(
                    f'INSERT INTO {connection.ops.quote_name(target_table)} '
                    f'SELECT * FROM {connection.ops.quote_name(source_table)}'
                )
                print(f'[api_protocol_backup] {source_table} -> {target_table}', flush=True)

    def restore_api_protocol_configs(self):
        round_count = 0
        cursor_id = 0
        total_updated = 0
        total_skipped = 0
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            api_infos = list(
                self.ApiInfo.objects.filter(id__gt=cursor_id)
                .order_by('id')
                .only('id', 'url', 'protocol_type')[:self.limit]
            )
            if not api_infos:
                break
            round_count += 1
            cursor_id = api_infos[-1].id
            legacy = self._legacy_rows(
                'api_info',
                [item.id for item in api_infos],
                ('method', 'headers', 'params', 'is_text_params', 'data', 'json', 'file',
                 'body_type', 'body_config', 'sse_config'),
            )
            updated = 0
            skipped = 0
            for api_info in api_infos:
                protocol_type = api_info.protocol_type or 'http'
                values = legacy.get(api_info.id, {})
                body_type, body_config = self._legacy_body_config(values)
                legacy_has_data = any(
                    values.get(field) not in (None, '', {}, [])
                    for field in ('method', 'headers', 'params', 'data', 'json', 'file', 'body_type', 'body_config', 'sse_config')
                )
                if protocol_type in ('http', 'sse'):
                    if not legacy_has_data and self.ApiInfoHttpConfig.objects.filter(api_info_id=api_info.id).exists():
                        skipped += 1
                        continue
                    if self.args.execute:
                        self.ApiInfoHttpConfig.objects.update_or_create(
                            api_info_id=api_info.id,
                            defaults={
                                'method': values.get('method') if values.get('method') is not None else 0,
                                'url': values.get('url') or api_info.url or '',
                                'headers': self._legacy_json(values.get('headers')),
                                'params': values.get('params'),
                                'is_text_params': values.get('is_text_params') if values.get('is_text_params') is not None else 1,
                                'body_type': body_type,
                                'body_config': body_config,
                                'sse_config': self._legacy_json(values.get('sse_config')),
                            },
                        )
                    updated += 1
                elif protocol_type == 'websocket':
                    if not legacy_has_data and self.ApiInfoWebSocketConfig.objects.filter(api_info_id=api_info.id).exists():
                        skipped += 1
                        continue
                    if self.args.execute:
                        self.ApiInfoWebSocketConfig.objects.update_or_create(
                            api_info_id=api_info.id,
                            defaults={
                                'url': values.get('url') or api_info.url or '',
                                'headers': self._legacy_json(values.get('headers')),
                                'params': values.get('params'),
                                'is_text_params': values.get('is_text_params') if values.get('is_text_params') is not None else 1,
                                'body_config': body_config,
                            },
                        )
                    updated += 1
                else:
                    skipped += 1
            total_updated += updated
            total_skipped += skipped
            self.print_counts(
                f'[api_protocol_restore round={round_count} '
                f'{"updated" if self.args.execute else "would_update"}={updated} skipped={skipped}]'
            )
            self._sleep()
        print(
            f'[api_protocol_restore done] '
            f'{"updated" if self.args.execute else "would_update"}={total_updated} skipped={total_skipped}',
            flush=True,
        )

    def restore_api_case_body_configs(self):
        round_count = 0
        cursor_id = 0
        total_updated = 0
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            parameters = list(
                self.ApiCaseDetailedParameter.objects.filter(id__gt=cursor_id)
                .order_by('id')
                .only('id', 'body_config')[:self.limit]
            )
            if not parameters:
                break
            round_count += 1
            cursor_id = parameters[-1].id
            legacy = self._legacy_rows(
                'api_case_detailed_parameter',
                [item.id for item in parameters],
                ('data', 'json', 'file', 'is_text_data', 'is_text_json', 'body_type', 'body_config'),
            )
            updated = 0
            for parameter in parameters:
                if parameter.body_config not in (None, '', {}, []):
                    continue
                body_type, body_config = self._legacy_body_config(legacy.get(parameter.id, {}))
                if body_config is None:
                    continue
                if self.args.execute:
                    self.ApiCaseDetailedParameter.objects.filter(id=parameter.id).update(
                        body_config=body_config,
                    )
                updated += 1
            total_updated += updated
            self.print_counts(
                f'[api_case_body_config round={round_count} '
                f'{"updated" if self.args.execute else "would_update"}={updated}]'
            )
            self._sleep()
        print(
            f'[api_case_body_config done] '
            f'{"updated" if self.args.execute else "would_update"}={total_updated}',
            flush=True,
        )

    def repair_current_api_protocol_revisions(self):
        releases = list(
            self.ApiInfoRelease.objects.filter(
                is_current=True,
                status=self.ApiInfoRelease.STATUS_PUBLISHED,
            ).select_related('revision')
        )
        updated = 0
        skipped = 0
        for release in releases:
            revision = release.revision
            payload = deepcopy(revision.payload or {})
            api_payload = payload.get('api_info') if isinstance(payload, dict) else None
            if not isinstance(api_payload, dict):
                api_payload = payload
            if api_payload.get('protocol_config'):
                skipped += 1
                continue
            api_info = self.ApiInfo.objects.get(id=release.api_info_id)
            runtime_payload = self.ApiInfoRuntimeService.current_payload(api_info)
            api_payload['protocol_config'] = deepcopy(runtime_payload.get('protocol_config'))
            if self.args.execute:
                revision.payload = payload
                revision.checksum = self.ApiCaseRevisionService.checksum(payload)
                revision.save(update_fields=['payload', 'checksum'])
            updated += 1
        self.print_counts(
            f'[api_protocol_revision {"updated" if self.args.execute else "would_update"}={updated} skipped={skipped}]'
        )

    def cleanup_empty_api_cases(self):
        """Clean API cases that cannot be versioned because they contain no steps."""
        round_count = 0
        cursor_id = 0
        total_deleted_cases = 0
        total_deleted_details = 0
        total_deleted_results = 0
        total_skipped = 0
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            case_ids = list(
                self.ApiCase.objects.filter(id__gt=cursor_id)
                .exclude(id__in=self.ApiCaseDetailed.objects.values('case_id'))
                .order_by('id')
                .values_list('id', flat=True)[:self.limit]
            )
            if not case_ids:
                break
            round_count += 1
            deleted_cases = 0
            deleted_details = 0
            deleted_results = 0
            skipped = 0
            for case_id in case_ids:
                cursor_id = max(cursor_id, case_id)
                if self.TasksDetails.objects.filter(api_case_id=case_id).exists():
                    skipped += 1
                    print(f'[cleanup_empty_case] skipped case_id={case_id}: 已绑定定时任务', flush=True)
                    continue
                detail_ids = list(
                    self.TestSuiteDetails.objects.filter(
                        type=self.TestCaseTypeEnum.API.value,
                        case_id=case_id,
                    ).values_list('id', flat=True)
                )
                result_count = self.ExecutionResult.objects.filter(
                    test_suite_detail_id__in=detail_ids,
                ).count() if detail_ids else 0
                if self.args.execute:
                    if detail_ids:
                        self.delete_execution_results_by_detail_ids(detail_ids)
                        self.TestSuiteDetails.objects.filter(id__in=detail_ids).delete()
                    self.ApiCase.objects.filter(id=case_id).delete()
                deleted_cases += 1
                deleted_details += len(detail_ids)
                deleted_results += result_count
                print(
                    f'[cleanup_empty_case] {"deleted" if self.args.execute else "would_delete"} '
                    f'case_id={case_id} report_details={len(detail_ids)} result_rows={result_count}',
                    flush=True,
                )
            total_deleted_cases += deleted_cases
            total_deleted_details += deleted_details
            total_deleted_results += deleted_results
            total_skipped += skipped
            self.print_counts(
                f'[cleanup_empty_case round={round_count} '
                f'{"deleted_cases" if self.args.execute else "would_delete_cases"}={deleted_cases} '
                f'report_details={deleted_details} result_rows={deleted_results} skipped={skipped}]'
            )
            self._sleep()
        print(
            f'[cleanup_empty_case done] '
            f'{"deleted_cases" if self.args.execute else "would_delete_cases"}={total_deleted_cases} '
            f'report_details={total_deleted_details} result_rows={total_deleted_results} skipped={total_skipped}',
            flush=True,
        )

    def delete_execution_results_by_detail_ids(self, detail_ids: list[int]):
        from django.core.files.storage import default_storage

        results = list(
            self.ExecutionResult.objects.filter(test_suite_detail_id__in=detail_ids).only('id', 'result_object_key')
        )
        for result in results:
            if not result.result_object_key:
                continue
            try:
                default_storage.delete(result.result_object_key)
            except Exception as error:
                print(
                    f'[execution_result] delete file failed result_id={result.id} '
                    f'object_key={result.result_object_key}: {error}',
                    flush=True,
                )
        self.ExecutionResult.objects.filter(id__in=[result.id for result in results]).delete()

    def clean_header_ids(self, header_ids):
        if not header_ids:
            return header_ids, False, []
        normalized_ids = []
        removed_ids = []
        for header_id in header_ids:
            try:
                normalized_ids.append(int(header_id))
            except (TypeError, ValueError):
                removed_ids.append(header_id)
        existing_ids = set(self.ApiHeaders.objects.filter(id__in=normalized_ids).values_list('id', flat=True))
        cleaned_ids = []
        for header_id in normalized_ids:
            if header_id in existing_ids:
                cleaned_ids.append(header_id)
            else:
                removed_ids.append(header_id)
        return cleaned_ids, cleaned_ids != header_ids, removed_ids

    def clean_case_missing_headers(self, case_id: int) -> list:
        removed = []
        api_case = self.ApiCase.objects.get(id=case_id)
        cleaned_front_headers, changed, removed_ids = self.clean_header_ids(api_case.front_headers or [])
        if changed:
            if self.args.execute:
                api_case.front_headers = cleaned_front_headers
                api_case.save(update_fields=['front_headers', 'update_time'])
            removed.extend(removed_ids)
        parameters = self.ApiCaseDetailedParameter.objects.filter(case_detailed__case_id=case_id).order_by('id')
        for parameter in parameters:
            cleaned_headers, changed, removed_ids = self.clean_header_ids(parameter.headers or [])
            if changed:
                if self.args.execute:
                    parameter.headers = cleaned_headers
                    parameter.save(update_fields=['headers', 'update_time'])
                removed.extend(removed_ids)
        return removed

    def migrate_api_info(self):
        round_count = 0
        cursor_id = 0
        total_created = 0
        total_failed = 0
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            ids = list(
                self.ApiInfo.objects.exclude(id__in=self._published_api_info_ids())
                .filter(id__gt=cursor_id)
                .order_by('id')
                .values_list('id', flat=True)[:self.limit]
            )
            if not ids:
                break
            round_count += 1
            created = 0
            failed = 0
            for api_info_id in ids:
                cursor_id = max(cursor_id, api_info_id)
                try:
                    if self.args.execute:
                        api_info = self.ApiInfo.objects.get(id=api_info_id)
                        operator_id = api_info.update_user_id
                        revision = self.ApiInfoRevisionService.record_current(
                            api_info_id,
                            operator_id=operator_id,
                            source='migration',
                            summary='7.1.0 历史接口配置迁移',
                        )
                        self.ApiInfoRevision.objects.filter(id=revision.id).update(source='migration')
                        release = self.ApiInfoRevisionService.publish(
                            api_info_id,
                            revision.id,
                            publisher_id=operator_id,
                            release_note='7.1.0 历史接口配置迁移自动发布',
                        )
                        self.ApiCaseDetailed.objects.filter(
                            api_info_id=api_info_id,
                            pinned_api_info_revision__isnull=True,
                        ).update(pinned_api_info_revision_id=release.revision_id)
                    created += 1
                except Exception as error:
                    failed += 1
                    print(f'[api_info] failed api_info_id={api_info_id}: {error}', flush=True)
            total_created += created
            total_failed += failed
            self.print_counts(f'[api_info round={round_count} {"created" if self.args.execute else "would_create"}={created} failed={failed}]')
            self._sleep()
        print(f'[api_info done] {"created" if self.args.execute else "would_create"}={total_created} failed={total_failed}', flush=True)

    def migrate_api_case(self):
        round_count = 0
        cursor_id = 0
        total_created = 0
        total_failed = 0
        failure_counter = Counter()
        failure_samples = defaultdict(list)
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            ids = list(
                self.ApiCase.objects.exclude(id__in=self._published_api_case_ids())
                .filter(id__gt=cursor_id)
                .order_by('id')
                .values_list('id', flat=True)[:self.limit]
            )
            if not ids:
                break
            round_count += 1
            created = 0
            failed = 0
            for case_id in ids:
                cursor_id = max(cursor_id, case_id)
                try:
                    if self.args.execute:
                        self._publish_case(case_id)
                    else:
                        self._validate_case_can_publish(case_id)
                    created += 1
                except Exception as error:
                    failed += 1
                    reason = str(error)
                    failure_counter[reason] += 1
                    if len(failure_samples[reason]) < self.args.failure_samples:
                        failure_samples[reason].append(case_id)
            total_created += created
            total_failed += failed
            self.print_counts(f'[api_case round={round_count} {"created" if self.args.execute else "would_create"}={created} failed={failed}]')
            self._sleep()
        print(f'[api_case done] {"created" if self.args.execute else "would_create"}={total_created} failed={total_failed}', flush=True)
        if failure_counter:
            print('[api_case failure summary]', flush=True)
            for reason, count in failure_counter.most_common(20):
                print(f'  count={count} samples={failure_samples[reason]} reason={reason}', flush=True)

    def _validate_case_can_publish(self, case_id: int):
        if not self.ApiCaseDetailed.objects.filter(case_id=case_id).exists():
            raise RuntimeError('用例修订不完整，禁止发布：至少需要一个接口步骤')
        for step in self.ApiCaseDetailed.objects.filter(case_id=case_id).order_by('id'):
            if not self.ApiInfoRelease.objects.filter(
                api_info_id=step.api_info_id,
                is_current=True,
                status=self.ApiInfoRelease.STATUS_PUBLISHED,
            ).exists():
                raise RuntimeError(f'步骤 {step.id} 绑定的 API Info {step.api_info_id} 没有当前发布版本')

    def _publish_case(self, case_id: int):
        api_case = self.ApiCase.objects.get(id=case_id)
        operator_id = api_case.update_user_id or api_case.case_people_id
        removed_header_ids = self.clean_case_missing_headers(case_id)
        if removed_header_ids:
            print(f'[api_case] cleaned missing headers case_id={case_id} removed={removed_header_ids}', flush=True)
        for step in self.ApiCaseDetailed.objects.filter(case_id=case_id).order_by('id'):
            release = self.ApiInfoRelease.objects.filter(
                api_info_id=step.api_info_id,
                is_current=True,
                status=self.ApiInfoRelease.STATUS_PUBLISHED,
            ).select_related('revision').first()
            if release is None:
                raise RuntimeError(f'步骤 {step.id} 绑定的 API Info {step.api_info_id} 没有当前发布版本')
            if step.pinned_api_info_revision_id != release.revision_id:
                step.pinned_api_info_revision_id = release.revision_id
                step.save(update_fields=['pinned_api_info_revision', 'update_time'])
        revision = self.ApiCaseRevisionService.record_current(
            case_id,
            operator_id=operator_id,
            source='migration',
            summary='7.1.0 历史用例配置迁移',
        )
        self.ApiCaseRevision.objects.filter(id=revision.id).update(source='migration')
        self.ApiCaseRevisionService._publish_revision(
            case_id,
            revision.id,
            publisher_id=operator_id,
            release_note='7.1.0 历史用例配置迁移自动发布',
        )

    def backfill_task_details(self):
        round_count = 0
        cursor_id = 0
        total_updated = 0
        total_skipped = 0
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            items = list(
                self.TasksDetails.objects.filter(
                    api_case_id__isnull=False,
                    api_case_revision_id__isnull=True,
                    id__gt=cursor_id,
                )
                .select_related('task')
                .order_by('id')[:self.limit]
            )
            if not items:
                break
            round_count += 1
            updated = 0
            skipped = 0
            from django.utils import timezone

            now = timezone.now()
            releases = {
                release.api_case_id: release
                for release in self.ApiCaseRelease.objects.filter(
                    api_case_id__in=[item.api_case_id for item in items],
                    is_current=True,
                    status=self.ApiCaseRelease.STATUS_PUBLISHED,
                ).select_related('revision')
            }
            for item in items:
                cursor_id = max(cursor_id, item.id)
                release = releases.get(item.api_case_id)
                if release is None:
                    skipped += 1
                    continue
                if self.args.execute:
                    self.TasksDetails.objects.filter(id=item.id).update(
                        api_case_revision_id=release.revision_id,
                        api_case_release_id=release.id,
                        version_policy=self.TaskCaseVersionPolicyEnum.PINNED.value,
                        bound_checksum=release.revision.checksum,
                        update_user_id=getattr(item.task, 'update_user_id', None),
                        bound_at=now,
                    )
                updated += 1
            total_updated += updated
            total_skipped += skipped
            self.print_counts(f'[task_detail round={round_count} {"updated" if self.args.execute else "would_update"}={updated} skipped={skipped}]')
            self._sleep()
        print(f'[task_detail done] {"updated" if self.args.execute else "would_update"}={total_updated} skipped={total_skipped}', flush=True)

    def backfill_test_suite_details(self):
        round_count = 0
        cursor_id = 0
        total_updated = 0
        total_skipped = 0
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            items = list(
                self.TestSuiteDetails.objects.filter(
                    type=self.TestCaseTypeEnum.API.value,
                    api_case_revision_id__isnull=True,
                    id__gt=cursor_id,
                )
                .order_by('id')[:self.limit]
            )
            if not items:
                break
            round_count += 1
            updated = 0
            skipped = 0
            releases = {
                release.api_case_id: release
                for release in self.ApiCaseRelease.objects.filter(
                    api_case_id__in=[item.case_id for item in items],
                    is_current=True,
                    status=self.ApiCaseRelease.STATUS_PUBLISHED,
                ).select_related('revision')
            }
            for item in items:
                cursor_id = max(cursor_id, item.id)
                release = releases.get(item.case_id)
                if release is None:
                    skipped += 1
                    continue
                if self.args.execute:
                    self.TestSuiteDetails.objects.filter(id=item.id).update(
                        api_case_revision_id=release.revision_id,
                        api_case_release_id=release.id,
                        config_checksum=release.revision.checksum,
                    )
                updated += 1
            total_updated += updated
            total_skipped += skipped
            self.print_counts(f'[test_suite_detail round={round_count} {"updated" if self.args.execute else "would_update"}={updated} skipped={skipped}]')
            self._sleep()
        print(f'[test_suite_detail done] {"updated" if self.args.execute else "would_update"}={total_updated} skipped={total_skipped}', flush=True)

    def backfill_report_summary(self):
        if self.args.days <= 0:
            raise RuntimeError('--days 必须大于 0')
        if self.args.max_result_mb < 0:
            raise RuntimeError('--max-result-mb 不能小于 0')
        from django.utils import timezone

        round_count = 0
        cursor_id = 0
        total_updated = 0
        total_failed = 0
        total_skipped = 0
        cutoff_time = timezone.now() - timedelta(days=self.args.days)
        base_queryset = self.TestSuiteDetails.objects.filter(create_time__gte=cutoff_time).order_by('id')
        if not self.args.force:
            base_queryset = base_queryset.filter(summary_data__isnull=True)
        if self.args.test_suite_id:
            base_queryset = base_queryset.filter(test_suite_id=self.args.test_suite_id)
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            detail_ids = list(base_queryset.filter(id__gt=cursor_id).values_list('id', flat=True)[:self.limit])
            if not detail_ids:
                break
            round_count += 1
            cursor_id = max(detail_ids)
            payload_metas = list(
                self.ExecutionResult.objects.filter(test_suite_detail_id__in=detail_ids, is_latest=True)
                .only('id', 'test_suite_detail_id', 'result_size')
                .order_by()
            )
            payload_meta_map = {payload.test_suite_detail_id: payload for payload in payload_metas}
            batch = []
            updated = 0
            failed = 0
            skipped = 0
            for detail_id in detail_ids:
                payload_meta = payload_meta_map.get(detail_id)
                if not payload_meta:
                    packed_summary_data = self.TestSuiteExecutionResultService.pack_summary_data([], {
                        'summary_status': 'skipped',
                        'summary_reason': 'result_payload_missing',
                    })
                    batch.append((self.TestSuiteDetails(id=detail_id, summary_data=packed_summary_data), 0))
                    skipped += 1
                    continue
                result_size_mb = (payload_meta.result_size or 0) / 1024 / 1024
                if self.args.verbose or result_size_mb >= self.args.large_log_mb:
                    print(
                        f'准备处理 detail_id={detail_id}, result_id={payload_meta.id}, '
                        f'result_size={result_size_mb:.2f}MB',
                        flush=True,
                    )
                if self.args.max_result_mb and result_size_mb > self.args.max_result_mb:
                    packed_summary_data = self.TestSuiteExecutionResultService.pack_summary_data([], {
                        'summary_status': 'skipped',
                        'summary_reason': 'result_size_exceeded',
                        'result_id': payload_meta.id,
                        'result_size': payload_meta.result_size or 0,
                        'max_result_mb': self.args.max_result_mb,
                    })
                    batch.append((self.TestSuiteDetails(id=detail_id, summary_data=packed_summary_data), 0))
                    skipped += 1
                    continue
                try:
                    payload = self.ExecutionResult.objects.select_related(
                        'test_suite_detail',
                        'test_suite_detail__test_suite',
                    ).get(id=payload_meta.id)
                    detail = payload.test_suite_detail
                    payload_result_data = self.ExecutionResultService.load_result_data(payload)
                    normalized_result = self.TestSuiteExecutionResultService.normalize_detail_result_data(
                        detail,
                        payload_result_data,
                    )
                    summary_data = self.TestSuiteExecutionResultService.build_summary_data(detail, normalized_result)
                    summary_meta = self.TestSuiteExecutionResultService.extract_api_snapshot_meta(payload_result_data)
                    packed_summary_data = self.TestSuiteExecutionResultService.pack_summary_data(summary_data, summary_meta)
                    summary_size = self.TestSuiteExecutionResultService.calc_result_size(packed_summary_data)
                    detail.summary_data = packed_summary_data
                    batch.append((detail, summary_size))
                    updated += 1
                    if self.args.verbose:
                        print(
                            f'id={payload.id}, detail_id={detail.id}, suite_id={detail.test_suite_id}, '
                            f'type={detail.type}, case_id={detail.case_id}, case_name={detail.case_name}, '
                            f'result_size={payload.result_size}, summary_size={summary_size}, '
                            f'{build_preview(summary_data)}, meta_keys={list((summary_meta or {}).keys())[:8]}',
                            flush=True,
                        )
                except Exception as error:
                    failed += 1
                    print(f'[report_summary] failed detail_id={detail_id}, result_id={payload_meta.id}: {error}', flush=True)
            if self.args.execute and batch:
                self.TestSuiteDetails.objects.bulk_update(
                    [detail for detail, _ in batch],
                    ['summary_data'],
                    batch_size=self.limit,
                )
            total_updated += updated
            total_failed += failed
            total_skipped += skipped
            self.print_counts(
                f'[report_summary round={round_count} {"updated" if self.args.execute else "would_update"}={updated} '
                f'failed={failed} skipped={skipped}]'
            )
            self._sleep()
        print(
            f'[report_summary done] {"updated" if self.args.execute else "would_update"}={total_updated} '
            f'failed={total_failed} skipped={total_skipped}',
            flush=True,
        )

    def repair_revision_payloads(self):
        round_count = 0
        cursor_id = 0
        total_updated = 0
        total_skipped = 0
        api_revision_cache: dict[int, Any] = {}
        while True:
            if self.args.max_rounds and round_count >= self.args.max_rounds:
                break
            revisions = list(self.ApiCaseRevision.objects.filter(id__gt=cursor_id).order_by('id')[:self.limit])
            if not revisions:
                break
            round_count += 1
            updated = 0
            skipped = 0
            for revision in revisions:
                cursor_id = max(cursor_id, revision.id)
                payload_model = self.ApiCaseRevisionPayloadModel.from_payload(deepcopy(revision.payload or {}))
                payload = payload_model.model_dump()
                changed = False
                for step in payload.get('api_case_detailed') or []:
                    api_info_revision_id = step.get('api_info_revision_id')
                    if not api_info_revision_id:
                        continue
                    api_revision = api_revision_cache.get(api_info_revision_id)
                    if api_revision is None:
                        api_revision = self.ApiInfoRevision.objects.filter(id=api_info_revision_id).first()
                        if api_revision is None:
                            continue
                        api_revision_cache[api_info_revision_id] = api_revision
                    if step.get('api_info_id') != api_revision.api_info_id:
                        step['api_info_id'] = api_revision.api_info_id
                        changed = True
                if changed or revision.payload != payload:
                    if self.args.execute:
                        revision.payload = payload
                        revision.checksum = self.ApiCaseRevisionService.checksum(payload)
                        revision.save(update_fields=['payload', 'checksum'])
                    updated += 1
                else:
                    skipped += 1
            total_updated += updated
            total_skipped += skipped
            self.print_counts(f'[repair round={round_count} {"updated" if self.args.execute else "would_update"}={updated} skipped={skipped}]')
            self._sleep()
        print(f'[repair done] {"updated" if self.args.execute else "would_update"}={total_updated} skipped={total_skipped}', flush=True)

    def _sleep(self):
        from django.db import close_old_connections

        close_old_connections()
        if self.args.sleep > 0:
            time.sleep(self.args.sleep)

    def run(self):
        print(
            f'[start] env={self.args.env} db={self.settings.DATABASES["default"]["NAME"]} '
            f'host={self.settings.DATABASES["default"]["HOST"]} mode={"execute" if self.args.execute else "dry-run"}',
            flush=True,
        )
        self.print_counts('[start]')
        if self.args.stage == 'status':
            self.print_counts('[finish]')
            return
        if self.args.stage == 'api_protocol_backup':
            if not self.args.execute:
                raise RuntimeError('api_protocol_backup 阶段必须传 --execute')
            self.backup_api_protocol_sources()
            self.print_counts('[finish]')
            return
        if self.args.stage in {'all', 'api_protocol_restore'}:
            self.restore_api_protocol_configs()
            self.restore_api_case_body_configs()
        if self.args.stage in {'all', 'api_protocol_revision'}:
            self.repair_current_api_protocol_revisions()
        if self.args.stage in {'all', 'cleanup'}:
            self.cleanup_empty_api_cases()
        if self.args.stage in {'all', 'api_info'}:
            self.migrate_api_info()
        if self.args.stage in {'all', 'api_case'}:
            self.migrate_api_case()
        if self.args.stage in {'all', 'task_detail'}:
            self.backfill_task_details()
        if self.args.stage in {'all', 'test_suite_detail'}:
            self.backfill_test_suite_details()
        if self.args.stage in {'all', 'repair'}:
            self.repair_revision_payloads()
        if self.args.stage in {'all', 'report_summary'}:
            self.backfill_report_summary()
        self.print_counts('[finish]')
        if not self.args.execute:
            print('No data changed. Add --execute to write data.', flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description='7.1.0 API版本数据迁移与测试报告摘要回填')
    parser.add_argument('--env', required=True, choices=('dev', 'test', 'master'))
    parser.add_argument(
        '--stage',
        default='all',
        choices=[
            'all',
            'cleanup',
            'api_info',
            'api_case',
            'api_protocol_backup',
            'api_protocol_restore',
            'api_protocol_revision',
            'task_detail',
            'test_suite_detail',
            'repair',
            'report_summary',
            'status',
        ],
    )
    parser.add_argument('--limit', type=int, default=100, help='单批处理数量，最大 500。')
    parser.add_argument('--sleep', type=float, default=0.2, help='每批处理后的等待秒数。')
    parser.add_argument('--max-rounds', type=int, default=0, help='每个阶段最多批次数，0 表示不限制。')
    parser.add_argument('--failure-samples', type=int, default=20, help='每类失败原因最多记录的 case id 数量。')
    parser.add_argument('--days', type=int, default=10, help='report_summary 阶段回填最近多少天报告摘要。')
    parser.add_argument('--test-suite-id', type=int, default=None, help='report_summary 阶段只处理指定测试报告。')
    parser.add_argument(
        '--backup-table-name',
        default=None,
        help='api_protocol_backup 阶段使用的备份表名前缀，例如 api_migration_731_20260725。',
    )
    parser.add_argument('--force', action='store_true', help='强制重刷已有 summary_data。')
    parser.add_argument('--max-result-mb', type=float, default=20, help='结果大于该 MB 时跳过摘要回填，0 表示不限制。')
    parser.add_argument('--retry-times', type=int, default=3, help='数据库断线后的重试次数。')
    parser.add_argument('--retry-sleep', type=float, default=5, help='数据库断线后的重试等待秒数。')
    parser.add_argument('--large-log-mb', type=float, default=5, help='结果大于该 MB 时打印明细日志。')
    parser.add_argument('--verbose', action='store_true', help='打印每条处理明细。')
    parser.add_argument('--execute', action='store_true', help='实际写入数据库。')
    args = parser.parse_args()
    if args.limit <= 0:
        raise ValueError('--limit 必须大于 0')
    if args.sleep < 0:
        raise ValueError('--sleep 不能小于 0')
    if args.max_rounds < 0:
        raise ValueError('--max-rounds 不能小于 0')
    if args.days <= 0:
        raise ValueError('--days 必须大于 0')
    if args.retry_times < 0:
        raise ValueError('--retry-times 不能小于 0')
    if args.retry_sleep < 0:
        raise ValueError('--retry-sleep 不能小于 0')
    if args.large_log_mb < 0:
        raise ValueError('--large-log-mb 不能小于 0')
    if args.max_result_mb < 0:
        raise ValueError('--max-result-mb 不能小于 0')
    return args


def main() -> None:
    args = parse_args()
    setup_django(args.env)
    MigrationRunner(args).run()


if __name__ == '__main__':
    main()
