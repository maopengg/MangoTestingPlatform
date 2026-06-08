# -*- coding: utf-8 -*-
import os
import posixpath
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.core.files.storage import default_storage
from minio import Minio
from minio_storage.storage import MinioMediaStorage


class MangoMinioMediaStorage(MinioMediaStorage):
    """MinIO storage with optional virtual-hosted-style S3 requests."""

    def __init__(self):
        super().__init__()
        self.location = f"auto_test_report/{os.getenv('DJANGO_ENV', 'master')}".strip('/')
        self.legacy_locations = [
            f"qfei-auto-platform/{os.getenv('DJANGO_ENV', 'master')}".strip('/'),
        ]
        if getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False):
            self.client._base_url.virtual_style_flag = True

    def _prefix_name(self, name: str) -> str:
        name = name.replace('\\', '/').lstrip('/')
        if not self.location:
            return name
        if name == self.location or name.startswith(f'{self.location}/'):
            return name
        for legacy_location in self.legacy_locations:
            if name == legacy_location or name.startswith(f'{legacy_location}/'):
                return name
        return posixpath.join(self.location, name)

    def _name_candidates(self, name: str) -> list[str]:
        name = name.replace('\\', '/').lstrip('/')
        candidates = [self._prefix_name(name)]
        for legacy_location in self.legacy_locations:
            legacy_name = (
                name
                if name == legacy_location or name.startswith(f'{legacy_location}/')
                else posixpath.join(legacy_location, name)
            )
            if legacy_name not in candidates:
                candidates.append(legacy_name)
        if name not in candidates:
            candidates.append(name)
        return candidates

    def _open(self, name, mode="rb"):
        for candidate in self._name_candidates(name):
            if super(MangoMinioMediaStorage, self).exists(candidate):
                return super()._open(candidate, mode)
        return super()._open(self._prefix_name(name), mode)

    def _save(self, name, content):
        return super()._save(self._prefix_name(name), content)

    def delete(self, name):
        for candidate in self._name_candidates(name):
            if super(MangoMinioMediaStorage, self).exists(candidate):
                return super().delete(candidate)
        return super().delete(self._prefix_name(name))

    def exists(self, name):
        return any(
            super(MangoMinioMediaStorage, self).exists(candidate)
            for candidate in self._name_candidates(name)
        )

    def url(self, name, *args, **kwargs):
        for candidate in self._name_candidates(name):
            if super(MangoMinioMediaStorage, self).exists(candidate):
                return super().url(candidate, *args, **kwargs)
        return super().url(self._prefix_name(name), *args, **kwargs)

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
        for candidate in self._name_candidates(name):
            if super(MangoMinioMediaStorage, self).exists(candidate):
                object_name = candidate
                break
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
