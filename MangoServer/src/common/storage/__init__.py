# -*- coding: utf-8 -*-
"""Shared object-storage implementation."""
import posixpath
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.core.files.storage import default_storage
from minio import Minio
from minio.error import S3Error
from minio_storage.storage import MinioMediaStorage

from src.common.exceptions import CommonError, STORAGE_FILE_NOT_FOUND


class MangoMinioMediaStorage(MinioMediaStorage):
    """MinIO storage with optional virtual-hosted-style S3 requests."""

    def __init__(self):
        super().__init__()
        self.location = str(getattr(settings, 'FILE_STORAGE_ROOT', 'mango-testing-platform/master')).strip('/\\')
        self.legacy_locations = [
            'auto_test_report/master',
            'auto_test_report/test',
            'auto_test_report/dev',
            'mango-testing-platform/test',
            'mango-testing-platform/dev',
        ]
        if getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False):
            self.client._base_url.virtual_style_flag = True

    def _relative_name(self, name: str) -> str:
        name = name.replace('\\', '/').lstrip('/')
        for location in [self.location, *self.legacy_locations]:
            if name == location:
                return ''
            if name.startswith(f'{location}/'):
                return name[len(location) + 1:]
        return name

    def _prefix_name(self, name: str) -> str:
        return posixpath.join(self.location, self._relative_name(name))

    @staticmethod
    def _raise_file_not_found(name: str, error: Exception | None = None):
        raise CommonError(STORAGE_FILE_NOT_FOUND, value=(name,), error=str(error) if error else None) from error

    @staticmethod
    def _is_no_such_key(error: Exception) -> bool:
        return isinstance(error, S3Error) and getattr(error, 'code', None) == 'NoSuchKey'

    def _name_candidates(self, name: str) -> list[str]:
        name = name.replace('\\', '/').lstrip('/')
        relative_name = self._relative_name(name)
        candidates = [posixpath.join(self.location, relative_name)]
        for legacy_location in self.legacy_locations:
            legacy_name = posixpath.join(legacy_location, relative_name)
            if legacy_name not in candidates:
                candidates.append(legacy_name)
        if name not in candidates:
            candidates.append(name)
        return candidates

    def _open(self, name, mode="rb"):
        try:
            for candidate in self._name_candidates(name):
                if super(MangoMinioMediaStorage, self).exists(candidate):
                    return super()._open(candidate, mode)
        except Exception as error:
            if self._is_no_such_key(error):
                self._raise_file_not_found(name, error)
            raise
        self._raise_file_not_found(name)

    def _save(self, name, content):
        return super()._save(self._prefix_name(name), content)

    def delete(self, name):
        for candidate in self._name_candidates(name):
            if super(MangoMinioMediaStorage, self).exists(candidate):
                return super().delete(candidate)
        return super().delete(self._prefix_name(name))

    def iter_current_files(self, prefix: str):
        """只枚举当前环境，不使用历史环境路径回退。"""
        root = self._prefix_name(prefix).rstrip('/') + '/'
        for item in self.client.list_objects(self.bucket_name, prefix=root, recursive=True):
            if not item.is_dir:
                yield item.object_name, item.last_modified

    def delete_current_file(self, name: str):
        return super().delete(self._prefix_name(name))

    def exists(self, name):
        try:
            return any(
                super(MangoMinioMediaStorage, self).exists(candidate)
                for candidate in self._name_candidates(name)
            )
        except Exception as error:
            if self._is_no_such_key(error):
                return False
            raise

    def url(self, name, *args, **kwargs):
        try:
            for candidate in self._name_candidates(name):
                if super(MangoMinioMediaStorage, self).exists(candidate):
                    return super().url(candidate, *args, **kwargs)
        except Exception as error:
            if self._is_no_such_key(error):
                self._raise_file_not_found(name, error)
            raise
        self._raise_file_not_found(name)

    def _public_presigned_url(self, name: str) -> str:
        public_base_url = getattr(settings, 'MINIO_PUBLIC_BASE_URL', '').strip()
        public_url = urlsplit(public_base_url)
        if not public_url.scheme or not public_url.netloc:
            return super().url(name)

        endpoint = public_url.netloc
        bucket_prefix = f'{self.bucket_name}.'
        if endpoint.startswith(bucket_prefix):
            endpoint = endpoint[len(bucket_prefix):]

        client_kwargs = {
            'access_key': settings.MINIO_STORAGE_ACCESS_KEY,
            'secret_key': settings.MINIO_STORAGE_SECRET_KEY,
            'secure': public_url.scheme == 'https',
        }
        region = getattr(settings, 'MINIO_STORAGE_REGION', None)
        if region:
            client_kwargs['region'] = region
        client = Minio(endpoint, **client_kwargs)
        if getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False):
            client._base_url.virtual_style_flag = True
        return client.presigned_get_object(self.bucket_name, name)

    def public_url(self, name: str) -> str:
        public_base_url = getattr(settings, 'MINIO_PUBLIC_BASE_URL', '').strip()
        object_name = self._prefix_name(name)
        try:
            for candidate in self._name_candidates(name):
                if super(MangoMinioMediaStorage, self).exists(candidate):
                    object_name = candidate
                    break
            else:
                self._raise_file_not_found(name)
        except Exception as error:
            if self._is_no_such_key(error):
                self._raise_file_not_found(name, error)
            raise
        if getattr(settings, 'MINIO_STORAGE_MEDIA_USE_PRESIGNED', False):
            return self._public_presigned_url(object_name)
        if not public_base_url:
            return self.url(name)
        encoded_name = quote(object_name.replace('\\', '/').lstrip('/'), safe='/')
        return f"{public_base_url.rstrip('/')}/{encoded_name}"


def build_public_file_url(name: str) -> str:
    if not name:
        return ''
    if hasattr(default_storage, 'public_url'):
        return default_storage.public_url(name)
    return default_storage.url(name)


def iter_current_storage_files(prefix: str):
    if hasattr(default_storage, 'iter_current_files'):
        yield from default_storage.iter_current_files(prefix)
        return
    directories = [prefix]
    while directories:
        directory = directories.pop()
        try:
            children, files = default_storage.listdir(directory)
        except FileNotFoundError:
            continue
        directories.extend(posixpath.join(directory, child) for child in children)
        for file_name in files:
            name = posixpath.join(directory, file_name)
            yield name, default_storage.get_modified_time(name)


def delete_current_storage_file(name: str):
    if hasattr(default_storage, 'delete_current_file'):
        return default_storage.delete_current_file(name)
    return default_storage.delete(name)
