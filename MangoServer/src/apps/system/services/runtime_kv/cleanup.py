import time

from django.db import connection, transaction
from django.db.models.functions import Now

from src.apps.system.exceptions import SYSTEM_RUNTIME_KV_INVALID, SystemError
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.models import RuntimeKVEntry


class RuntimeKVCleanupService:
    @staticmethod
    def cleanup_expired(batch_size=500, max_batches=20, max_seconds=10, namespace=None):
        if any(type(value) is not int for value in (batch_size, max_batches, max_seconds)) or not (
            1 <= batch_size <= 500 and 1 <= max_batches <= 20 and 1 <= max_seconds <= 30
        ):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        if namespace is not None and not isinstance(namespace, RuntimeKVNamespaceEnum):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        # 新表由用户迁移创建，滚动部署期间调度器不应因尚未迁移持续报错。
        if RuntimeKVEntry._meta.db_table not in connection.introspection.table_names():
            return {'status': 'pending_migration', 'deleted_count': 0, 'batches': 0, 'duration': 0}
        start, deleted, batches = time.monotonic(), 0, 0
        queryset = RuntimeKVEntry.objects.all()
        if namespace is not None:
            queryset = queryset.filter(namespace=namespace.value)
        for _ in range(max_batches):
            if time.monotonic() - start >= max_seconds:
                break
            with transaction.atomic():
                ids = list(queryset.select_for_update(
                    skip_locked=connection.features.has_select_for_update_skip_locked,
                ).filter(
                    expires_at__lte=Now(),
                ).order_by('expires_at', 'id').values_list('pk', flat=True)[:batch_size])
                if not ids:
                    break
                deleted += queryset.filter(pk__in=ids, expires_at__lte=Now()).delete()[0]
            batches += 1
        return {'deleted_count': deleted, 'batches': batches, 'duration': round(time.monotonic() - start, 3)}
