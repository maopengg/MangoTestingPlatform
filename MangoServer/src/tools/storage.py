# -*- coding: utf-8 -*-
import os
import posixpath

from django.conf import settings
from minio_storage.storage import MinioMediaStorage


class MangoMinioMediaStorage(MinioMediaStorage):
    """MinIO storage with optional virtual-hosted-style S3 requests."""

    def __init__(self):
        super().__init__()
        self.location = f"qfei-auto-platform/{os.getenv('DJANGO_ENV', 'master')}".strip('/')
        if getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False):
            self.client._base_url.virtual_style_flag = True

    def _prefix_name(self, name: str) -> str:
        name = name.replace('\\', '/').lstrip('/')
        if not self.location:
            return name
        if name == self.location or name.startswith(f'{self.location}/'):
            return name
        return posixpath.join(self.location, name)

    def _save(self, name, content):
        return super()._save(self._prefix_name(name), content)

    def exists(self, name):
        return super().exists(self._prefix_name(name))
