import io
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit
from django.utils import timezone

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from minio import Minio
from urllib3 import PoolManager
from urllib3.util import Timeout
from tos import TosClientV2
from tos.enum import HttpMethodType

from src.apps.test_center.constants import OFFLINE_REPORT_MAX_BYTES
from src.apps.test_center.exceptions import REPORT_ARTIFACT_FAILED, TestCenterError


class ReportStorageService:
    """报告使用独立前缀；本地文件放在非公开目录，仅通过鉴权下载。"""

    def __init__(self, *, public_base=None):
        backend = getattr(settings, 'FILE_STORAGE_BACKEND', 'local')
        self.identity = {
            'backend': backend,
            'endpoint': getattr(settings, 'MINIO_STORAGE_ENDPOINT', ''),
            'bucket': getattr(settings, 'MINIO_STORAGE_MEDIA_BUCKET_NAME', ''),
            'location': str(Path(settings.RUNTIME_DIR) / 'report_artifacts') if backend == 'local' else (
                str(getattr(settings, 'FILE_STORAGE_ROOT', '')).strip('/')
            ),
        }
        self.secure = getattr(settings, 'MINIO_STORAGE_USE_HTTPS', True)
        self.virtual = getattr(settings, 'MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE', False)
        self.region = getattr(settings, 'MINIO_STORAGE_REGION', None) or (
            'cn-beijing' if backend == 'tos' else 'us-east-1'
        )
        self.public_base = public_base or getattr(settings, 'MINIO_PUBLIC_BASE_URL', '')
        self.local = FileSystemStorage(location=self.identity['location']) if backend == 'local' else None

    def _client(self, public=False):
        endpoint = self.identity['endpoint']
        secure, virtual = self.secure, self.virtual
        if public:
            if not self.public_base:
                raise TestCenterError(REPORT_ARTIFACT_FAILED)
            url = urlsplit(self.public_base)
            if url.scheme not in ('http', 'https') or not url.hostname:
                raise TestCenterError(REPORT_ARTIFACT_FAILED)
            endpoint, secure = url.netloc, url.scheme == 'https'
            prefix = self.identity['bucket'] + '.'
            if endpoint.startswith(prefix):
                endpoint, virtual = endpoint[len(prefix):], True
            if url.path.strip('/') not in ('', self.identity['bucket']):
                raise TestCenterError(REPORT_ARTIFACT_FAILED)
        access, secret = self._credentials()
        if not access or not secret or not endpoint or not self.identity['bucket']:
            raise TestCenterError(REPORT_ARTIFACT_FAILED)
        client = Minio(endpoint, access_key=access, secret_key=secret, secure=secure, region=self.region,
                       http_client=PoolManager(timeout=Timeout(connect=5, read=30), retries=False))
        client._base_url.virtual_style_flag = virtual
        return client

    def _credentials(self):
        return getattr(settings, 'MINIO_STORAGE_ACCESS_KEY', ''), getattr(settings, 'MINIO_STORAGE_SECRET_KEY', '')

    def _tos_client(self):
        access, secret = self._credentials()
        if not access or not secret or not self.identity['bucket'] or not self.identity['endpoint']:
            raise TestCenterError(REPORT_ARTIFACT_FAILED)
        endpoint = self.identity['endpoint']
        if endpoint.startswith('tos-s3-'):
            endpoint = endpoint.replace('tos-s3-', 'tos-', 1)
        return TosClientV2(access, secret, ('https://' if self.secure else 'http://') + endpoint,
                           self.region, max_retry_count=0, connection_time=5, request_timeout=30, socket_timeout=30)

    def _native_tos_storage(self):
        # 公共存储可能使用 S3 兼容地址，必须沿用 AWS4 签名，不能直接交给原生 SDK。
        return self.identity['backend'] == 'tos' and not self.identity['endpoint'].startswith('tos-s3-')

    def key(self, artifact_id):
        prefix = self.identity['location'] if self.local is None else ''
        return '/'.join(filter(None, (prefix, 'offline_reports', timezone.now().strftime('%Y/%m/%d'), f'{artifact_id}.html')))

    def save(self, key, content):
        if self.local is not None:
            if self.local.exists(key):
                self.local.delete(key)
            self.local.save(key, ContentFile(content))
        elif self._native_tos_storage():
            client = self._tos_client()
            try:
                client.put_object(self.identity['bucket'], key, content=content, content_length=len(content), content_type='text/html; charset=utf-8')
            finally:
                client.close()
        else:
            self._client().put_object(self.identity['bucket'], key, io.BytesIO(content), len(content), content_type='text/html; charset=utf-8')

    def read(self, key):
        limit = OFFLINE_REPORT_MAX_BYTES
        if self.local is not None:
            with self.local.open(key, 'rb') as file:
                result = file.read(limit + 1)
        elif self._native_tos_storage():
            client = self._tos_client()
            try:
                response = client.get_object(self.identity['bucket'], key)
                result = response.read(limit + 1)
            finally:
                client.close()
        else:
            response = self._client().get_object(self.identity['bucket'], key)
            try:
                result = response.read(limit + 1)
            finally:
                response.close()
                response.release_conn()
        if len(result) > limit:
            raise TestCenterError(REPORT_ARTIFACT_FAILED)
        return result

    def delete(self, key):
        if self.local is not None:
            self.local.delete(key)
        elif self._native_tos_storage():
            client = self._tos_client()
            try:
                client.delete_object(self.identity['bucket'], key)
            finally:
                client.close()
        else:
            self._client().remove_object(self.identity['bucket'], key)

    def url(self, key, filename, seconds, download=False):
        if self.local is not None:
            raise TestCenterError(REPORT_ARTIFACT_FAILED)
        disposition = 'attachment' if download else 'inline'
        headers = {'response-content-type': 'text/html; charset=utf-8',
                   'response-content-disposition': f'{disposition}; filename="{filename}"'}
        if self.identity['backend'] == 'tos':
            url = urlsplit(self.public_base)
            if url.scheme not in ('http', 'https') or not url.hostname or url.path not in ('', '/'):
                raise TestCenterError(REPORT_ARTIFACT_FAILED)
            bucket_prefix = self.identity['bucket'] + '.'
            bucket_host = url.hostname.removeprefix(bucket_prefix)
            if bucket_host.split('.')[0] == f'tos-s3-{self.region}':
                return self._client(public=True).presigned_get_object(
                    self.identity['bucket'], key, expires=timedelta(seconds=max(1, seconds)),
                    response_headers=headers,
                )
            custom_domain = bucket_host.split('.')[0] != f'tos-{self.region}'
            # 标准桶域名由 SDK 添加 Bucket；绑定域名则必须按原域名签名。
            alternative = self.public_base
            if not custom_domain and url.hostname.startswith(bucket_prefix):
                alternative = f'{url.scheme}://{url.netloc[len(bucket_prefix):]}'
            client = self._tos_client()
            try:
                return client.pre_signed_url(HttpMethodType.Http_Method_Get, self.identity['bucket'], key,
                    expires=max(1, seconds), query=headers, alternative_endpoint=alternative,
                    is_custom_domain=custom_domain).signed_url
            finally:
                client.close()
        # 响应头与最终客户端域名必须一起参与签名，签名后不得替换域名。
        return self._client(public=True).presigned_get_object(
            self.identity['bucket'], key, expires=timedelta(seconds=max(1, seconds)),
            response_headers=headers,
        )
