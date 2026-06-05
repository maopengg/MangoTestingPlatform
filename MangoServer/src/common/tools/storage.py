# -*- coding: utf-8 -*-
import os
import posixpath

from django.conf import settings
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
