from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from src.apps.system.exceptions import (
    SYSTEM_DIAGNOSTIC_BINDING_REPORT_UNSUPPORTED,
    SYSTEM_DIAGNOSTIC_BINDING_REPORT_NOT_FOUND,
    SYSTEM_DIAGNOSTIC_FILE_REPORT_INVALID,
    SYSTEM_DIAGNOSTIC_REPORT_REQUIRED,
    SYSTEM_DIAGNOSTIC_REPORT_TOO_LONG,
    SYSTEM_DIAGNOSTIC_BINDING_REPORT_INVALID,
    SYSTEM_DIAGNOSTIC_FILE_READ_REPORT_NOT_FOUND,
)
from src.apps.task_center.models import Tasks
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import TestSuite
from src.common.logging import log
from src.common.storage import build_public_file_url, delete_current_storage_file, iter_current_storage_files


class DiagnosticMarkdownService:
    TARGET_SCHEDULED_TASK = 'scheduled_task'
    TARGET_TEST_REPORT = 'test_report'
    ROOT_DIRECTORY = 'diagnostics'
    MAX_BYTES = 5 * 1024 * 1024
    _MODEL_MAP = {
        TARGET_SCHEDULED_TASK: (Tasks, 'scheduled-tasks'),
        TARGET_TEST_REPORT: (TestSuite, 'test-reports'),
    }

    @classmethod
    def save(cls, target_type: str, target_id: int, file_name: str, markdown_content: str) -> dict:
        model, directory = cls._target_config(target_type)
        target = model.objects.filter(id=target_id).first()
        if not target:
            raise TestCenterError(SYSTEM_DIAGNOSTIC_BINDING_REPORT_NOT_FOUND)

        safe_name = cls._safe_file_name(file_name)
        content = str(markdown_content or '').strip()
        if not content:
            raise TestCenterError(SYSTEM_DIAGNOSTIC_REPORT_REQUIRED)
        payload = content.encode('utf-8')
        if len(payload) > cls.MAX_BYTES:
            raise TestCenterError(SYSTEM_DIAGNOSTIC_REPORT_TOO_LONG)

        timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')
        storage_name = cls._build_storage_name(
            directory,
            target.id,
            timestamp,
            safe_name,
        )
        old_path = target.diagnostic_file_path
        saved_path = default_storage.save(storage_name, ContentFile(payload))
        try:
            target.diagnostic_file_path = saved_path
            # 绑定排查文档不属于任务配置或执行报告本身的业务更新，避免改变列表排序时间。
            target.save(update_fields=['diagnostic_file_path'])
        except Exception:
            default_storage.delete(saved_path)
            raise
        if old_path and old_path != saved_path:
            try:
                default_storage.delete(old_path)
            except Exception:
                log.system.exception('旧排查文档删除失败，等待定时清理')
        return cls.metadata(target_type, target)

    @classmethod
    def cleanup_expired(cls, retention_days: int) -> dict:
        cutoff = timezone.now() - timedelta(days=retention_days)
        root = str(getattr(settings, 'FILE_STORAGE_ROOT', '')).strip('/\\')
        models = {directory: model for model, directory in cls._MODEL_MAP.values()}
        pattern = re.compile(
            r'^diagnostics/(scheduled-tasks|test-reports)/(\d+)/(\d{20})-[^/]+\.md$'
        )
        deleted = failed = 0
        scan_failed = False
        try:
            for name, modified_at in iter_current_storage_files(cls.ROOT_DIRECTORY):
                relative = name[len(root) + 1:] if root and name.startswith(root + '/') else name
                match = pattern.fullmatch(relative)
                if not match or modified_at is None:
                    continue
                try:
                    file_date = datetime.strptime(match.group(3), '%Y%m%d%H%M%S%f').date()
                except ValueError:
                    continue
                modified_date = timezone.localtime(modified_at).date() if timezone.is_aware(modified_at) else modified_at.date()
                if file_date >= cutoff.date() or modified_date >= cutoff.date():
                    continue
                try:
                    with transaction.atomic():
                        # 条件更新保护并发上传的新绑定；删除失败会回滚解绑。
                        models[match.group(1)].objects.filter(
                            id=int(match.group(2)),
                            diagnostic_file_path__in=[name, relative],
                        ).update(diagnostic_file_path=None)
                        delete_current_storage_file(name)
                    deleted += 1
                except Exception:
                    failed += 1
                    log.system.exception(f'过期排查文档清理失败，下次重试：path={name}')
        except Exception:
            scan_failed = True
            log.system.exception('过期排查文档扫描失败，下次重试')
        return {
            'diagnostic_deleted_file_count': deleted,
            'diagnostic_failed_file_count': failed,
            'diagnostic_storage_scan_failed': scan_failed,
        }

    @classmethod
    def read(cls, target_type: str, target) -> dict:
        path = target.diagnostic_file_path
        if not path:
            raise TestCenterError(SYSTEM_DIAGNOSTIC_BINDING_REPORT_INVALID)
        try:
            with default_storage.open(path, 'rb') as file_obj:
                content = file_obj.read().decode('utf-8')
        except (OSError, UnicodeDecodeError, ValueError):
            raise TestCenterError(SYSTEM_DIAGNOSTIC_FILE_READ_REPORT_NOT_FOUND)
        return {**cls.metadata(target_type, target), 'content': content}

    @classmethod
    def metadata(cls, target_type: str, target) -> dict:
        path = target.diagnostic_file_path or ''
        stored_file_name = Path(path).name if path else ''
        display_file_name = re.sub(r'^\d{20}-', '', stored_file_name)
        update_time = target.update_time
        if path:
            try:
                update_time = default_storage.get_modified_time(path)
            except (NotImplementedError, OSError, ValueError):
                pass
        return {
            'target_type': target_type,
            'target_id': target.id,
            'file_path': path,
            'file_name': display_file_name or None,
            'download_url': build_public_file_url(path) if path else None,
            'update_time': update_time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    @classmethod
    def _target_config(cls, target_type: str):
        config = cls._MODEL_MAP.get(target_type)
        if not config:
            raise TestCenterError(SYSTEM_DIAGNOSTIC_BINDING_REPORT_UNSUPPORTED)
        return config

    @classmethod
    def _build_storage_name(
            cls,
            directory: str,
            target_id: int,
            timestamp: str,
            file_name: str,
    ) -> str:
        return f'{cls.ROOT_DIRECTORY}/{directory}/{target_id}/{timestamp}-{file_name}'

    @staticmethod
    def _safe_file_name(file_name: str) -> str:
        name = Path(str(file_name or '')).name
        if not name.lower().endswith('.md'):
            raise TestCenterError(SYSTEM_DIAGNOSTIC_FILE_REPORT_INVALID)
        stem = re.sub(r'[^0-9A-Za-z._\u4e00-\u9fff-]+', '-', name[:-3]).strip('.-')
        return f'{stem or "diagnostic"}.md'
