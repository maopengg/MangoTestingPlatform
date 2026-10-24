from datetime import datetime

from django.core.cache import cache
from django.db import connection, transaction
from django.db.models import QuerySet
from django.utils import timezone

from src.apps.auto_api.models import ApiMockConfig, ApiMockRequestLog
from src.apps.auto_api.services.mock_runtime import (
    MOCK_LOG_CLEAR_MARKER_TIMEOUT_SECONDS,
    MOCK_LOG_GLOBAL_CLEAR_TIMEOUT_SECONDS,
    MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY,
    MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY,
    mock_log_clear_marker_key,
)


class MockRequestLogCleanupService:
    DEFAULT_BATCH_SIZE = 5000

    @classmethod
    def clear_all_logs(cls) -> int:
        """暂停异步日志写入并清空整张日志表，立即释放 MySQL 物理空间。"""
        cleared_at = timezone.now()
        cache.set_many(
            {
                MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY: True,
                MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY: cleared_at,
            },
            MOCK_LOG_GLOBAL_CLEAR_TIMEOUT_SECONDS,
        )
        cleared = False
        try:
            # 暂停后统计，保证返回值与本次 TRUNCATE 清理的数据量一致。
            deleted_count = ApiMockRequestLog.objects.count()
            table_name = connection.ops.quote_name(ApiMockRequestLog._meta.db_table)
            with connection.cursor() as cursor:
                if connection.vendor == "mysql":
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
                else:
                    # 本地和单元测试数据库可能不是 MySQL；生产 MySQL 始终走 TRUNCATE。
                    cursor.execute(f"DELETE FROM {table_name}")
            cleared = True
            return deleted_count
        finally:
            cache.delete(MOCK_LOG_GLOBAL_WRITE_PAUSE_KEY)
            if not cleared:
                cache.delete(MOCK_LOG_GLOBAL_CLEAR_MARKER_KEY)

    @classmethod
    def clear_config_logs(
            cls,
            config_id: int,
            batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> int:
        """删除清空动作开始前的日志，并保留随后产生的新日志。"""
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")

        # Mock 日志写入也会锁配置行。这里只在建立清理快照时短暂加锁：
        # 先等待已开始的批量写入结束，再设置标记阻止旧队列数据回写。
        with transaction.atomic():
            ApiMockConfig.objects.select_for_update().only("id").get(pk=config_id)
            cleared_at = timezone.now()
            cache.set(
                mock_log_clear_marker_key(config_id),
                cleared_at,
                MOCK_LOG_CLEAR_MARKER_TIMEOUT_SECONDS,
            )

        queryset = ApiMockRequestLog.objects.filter(
            mock_config_id=config_id,
            create_time__lte=cleared_at,
        )
        return cls._delete_in_batches(queryset, batch_size=batch_size)

    @classmethod
    def cleanup_before(
            cls,
            cutoff_time: datetime,
            batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> int:
        queryset = ApiMockRequestLog.objects.filter(create_time__lt=cutoff_time)
        return cls._delete_in_batches(queryset, batch_size=batch_size)

    @classmethod
    def _delete_in_batches(cls, queryset: QuerySet, batch_size: int) -> int:
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")

        deleted_count = 0
        while True:
            # 清除 Model 默认排序，让 MySQL 直接选择过滤条件对应的索引。
            # 对百万级日志按 id 排序会造成大范围 filesort，反而放大清理开销。
            ids = list(
                queryset.order_by()
                .values_list("id", flat=True)[:batch_size]
            )
            if not ids:
                return deleted_count

            # 每批独立提交，避免百万行 DELETE 持有长事务、锁和巨量 undo 日志。
            with transaction.atomic():
                current_count, _ = ApiMockRequestLog.objects.filter(id__in=ids).delete()
            deleted_count += current_count
