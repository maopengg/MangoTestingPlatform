# -*- coding: utf-8 -*-
import os
import posixpath
import re
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from src.apps.test_center.exceptions import (
    EXECUTION_ARTIFACT_PATH_INVALID,
    EXECUTION_ARTIFACT_PATH_REQUIRED,
    TestCenterError,
)
from src.apps.test_center.services.storage.save_minio import SaveMinio
from src.common.logging import log
from src.common.storage import build_public_file_url, delete_current_storage_file, iter_current_storage_files


class ExecutionArtifactService:
    """Resolve persisted UI execution artifact paths to temporary browser URLs."""

    LEGACY_DIRECTORIES = {'screenshot', 'video'}
    PERF_CAPTURE_DIRECTORY = 'perf/capture'

    @classmethod
    def root_dir(cls) -> str:
        return str(getattr(settings, 'UI_EXECUTION_ARTIFACT_ROOT_DIR', 'uitest') or 'uitest').strip('/\\')

    @classmethod
    def screenshot_dir(cls) -> str:
        return posixpath.join(cls.root_dir(), 'screenshot')

    @classmethod
    def videos_dir(cls) -> str:
        return posixpath.join(cls.root_dir(), 'videos')

    @classmethod
    def allowed_directories(cls) -> set[str]:
        return {cls.screenshot_dir(), cls.videos_dir(), cls.PERF_CAPTURE_DIRECTORY, *cls.LEGACY_DIRECTORIES}

    @classmethod
    def normalize_directory(cls, value: str) -> str:
        directory = str(value or '').replace('\\', '/').strip('/')
        if directory == 'video':
            directory = cls.videos_dir()
        elif directory == 'screenshot':
            directory = cls.screenshot_dir()
        if directory not in cls.allowed_directories():
            return cls.screenshot_dir()
        return directory

    @classmethod
    def save_upload(cls, uploaded_file, file_dir: str) -> str:
        directory = cls.normalize_directory(file_dir)
        if getattr(settings, 'OBJECT_STORAGE_ENABLED', False):
            return SaveMinio(directory).main(uploaded_file)

        cls.cleanup_local_expired()
        file_name = posixpath.basename(uploaded_file.name)
        storage_name = default_storage.save(posixpath.join(directory, file_name), uploaded_file)
        return posixpath.join('mango-file', storage_name).replace('\\', '/')

    @classmethod
    def cleanup_local_expired(cls) -> int:
        if getattr(settings, 'OBJECT_STORAGE_ENABLED', False):
            return 0
        media_root = getattr(settings, 'MEDIA_ROOT', '')
        if not media_root:
            return 0
        artifact_root = os.path.join(media_root, cls.root_dir())
        if not os.path.isdir(artifact_root):
            return 0
        from src.apps.system.services.configuration.system_config import SystemConfigService

        retention_days = SystemConfigService.get_ranged_int('UI_ARTIFACT_RETENTION_DAYS')
        cutoff_timestamp = (timezone.now() - timedelta(days=retention_days)).timestamp()
        deleted = 0
        for root, _, files in os.walk(artifact_root):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    if os.path.getmtime(file_path) < cutoff_timestamp:
                        os.remove(file_path)
                        deleted += 1
                except OSError as error:
                    log.system.warning(f'本地UI执行产物清理失败，路径：{file_path}，错误：{error}')
        return deleted

    @classmethod
    def cleanup_expired(cls) -> dict:
        """递归回收当前环境的截图、录屏和智能执行证据。"""
        from src.apps.system.services.configuration.system_config import SystemConfigService

        days = SystemConfigService.get_ranged_int('UI_ARTIFACT_RETENTION_DAYS')
        cutoff = timezone.now() - timedelta(days=days)
        directories = {cls.screenshot_dir(), cls.videos_dir(), posixpath.join(cls.root_dir(), 'video'), *cls.LEGACY_DIRECTORIES}
        agent_directory = 'uitest/agent-executions'
        directories.add(agent_directory)
        extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.mp4', '.webm', '.mov', '.mkv'}
        root = str(getattr(settings, 'FILE_STORAGE_ROOT', '')).strip('/\\')
        deleted = failed = 0
        scan_failed = False
        for directory in sorted(directories):
            if not directory or any(part in {'.', '..'} for part in directory.split('/')):
                scan_failed = True
                log.system.error('UI执行产物目录无效，跳过清理')
                continue
            try:
                for name, modified_at in iter_current_storage_files(directory):
                    relative = name[len(root) + 1:] if root and name.startswith(root + '/') else name
                    if not relative.startswith(directory + '/') or modified_at is None:
                        continue
                    if directory == agent_directory:
                        if not re.fullmatch(r'uitest/agent-executions/\d{4}/\d{2}/\d{2}/[0-9a-f]{32}/[0-9a-f]{32}-[^/]+', relative):
                            continue
                    elif posixpath.splitext(relative)[1].lower() not in extensions:
                        continue
                    modified_date = timezone.localtime(modified_at).date() if timezone.is_aware(modified_at) else modified_at.date()
                    if modified_date >= cutoff.date():
                        continue
                    try:
                        delete_current_storage_file(name)
                        deleted += 1
                    except Exception:
                        failed += 1
                        log.system.exception(f'UI执行产物删除失败，下次重试：path={name}')
            except Exception:
                scan_failed = True
                log.system.exception(f'UI执行产物扫描失败，下次重试：directory={directory}')
        return {
            'ui_artifact_retention_days': days,
            'ui_artifact_deleted_file_count': deleted,
            'ui_artifact_failed_file_count': failed,
            'ui_artifact_storage_scan_failed': scan_failed,
        }

    @classmethod
    def cleanup_perf_captures(cls, retention_days: int) -> dict:
        cutoff = (timezone.now() - timedelta(days=retention_days)).date()
        root = str(getattr(settings, 'FILE_STORAGE_ROOT', '')).strip('/\\')
        deleted = failed = 0
        scan_failed = False
        try:
            for name, modified_at in iter_current_storage_files(cls.PERF_CAPTURE_DIRECTORY):
                relative = name[len(root) + 1:] if root and name.startswith(root + '/') else name
                if not re.fullmatch(r'perf/capture/perf-run-\d+-node-\d+\.csv', relative) or modified_at is None:
                    continue
                modified_date = timezone.localtime(modified_at).date() if timezone.is_aware(modified_at) else modified_at.date()
                if modified_date >= cutoff:
                    continue
                try:
                    delete_current_storage_file(name)
                    deleted += 1
                except Exception:
                    failed += 1
                    log.system.exception(f'性能抓包删除失败，下次重试：path={name}')
        except Exception:
            scan_failed = True
            log.system.exception('性能抓包扫描失败，下次重试')
        return {
            'perf_capture_deleted_file_count': deleted,
            'perf_capture_failed_file_count': failed,
            'perf_capture_storage_scan_failed': scan_failed,
        }

    @classmethod
    def normalize_path(cls, value: str) -> str:
        raw_value = str(value or '').strip()
        if not raw_value:
            raise TestCenterError(EXECUTION_ARTIFACT_PATH_REQUIRED)
        parsed = urlsplit(raw_value)
        if parsed.scheme and parsed.netloc:
            return raw_value

        path = parsed.path.replace('\\', '/').lstrip('/')
        if path.startswith('minio/'):
            path = path[len('minio/'):]
        bucket_name = getattr(settings, 'MINIO_STORAGE_MEDIA_BUCKET_NAME', '')
        bucket_prefix = f'{bucket_name}/' if bucket_name else ''
        if bucket_prefix and path.startswith(bucket_prefix):
            path = path[len(bucket_prefix):]

        parts = [part for part in path.split('/') if part]
        allowed_directories = cls.allowed_directories()
        object_directory = '/'.join(parts[2:-1]) if len(parts) >= 4 else ''
        local_directory = '/'.join(parts[1:-1]) if len(parts) >= 3 else ''
        object_storage_path = len(parts) >= 4 and parts[0] in {'auto_test_report',
                                                               'mango-testing-platform'} and object_directory in allowed_directories
        local_storage_path = len(parts) >= 3 and parts[0] == 'mango-file' and local_directory in allowed_directories
        if '..' in parts or not (object_storage_path or local_storage_path):
            raise TestCenterError(EXECUTION_ARTIFACT_PATH_INVALID)
        return '/'.join(parts)

    @classmethod
    def public_url(cls, value: str) -> str:
        normalized_path = cls.normalize_path(value)
        parsed = urlsplit(normalized_path)
        if parsed.scheme and parsed.netloc:
            return normalized_path
        if normalized_path.startswith('mango-file/'):
            return build_public_file_url(normalized_path[len('mango-file/'):])
        return build_public_file_url(normalized_path)
