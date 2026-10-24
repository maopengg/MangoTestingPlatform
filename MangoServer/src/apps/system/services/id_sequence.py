import time

from django.db import connections

from src.apps.system.constants import SNOWFLAKE_SEQUENCE_KEY
from src.apps.system.enums.cache import SystemConfigManagementLevelEnum
from src.apps.system.exceptions import SYSTEM_ID_SEQUENCE_EXHAUSTED, SystemError
from src.apps.system.models import CacheData


def reserve_snowflake_block() -> tuple[int, int]:
    # 独立自动提交连接使号段不随用例/工厂外层事务回滚而复用。
    connection = connections['id_allocator']
    try:
        if connection.in_atomic_block or not connection.get_autocommit():
            raise SystemError(SYSTEM_ID_SEQUENCE_EXHAUSTED)
        sequences = CacheData.objects.using('id_allocator').filter(key=SNOWFLAKE_SEQUENCE_KEY)
        if not sequences.exists():
            # 内部专用写入绕过普通配置的保护；并发首次初始化由 key 唯一索引仲裁。
            CacheData.objects.using('id_allocator').bulk_create([
                CacheData(
                    key=SNOWFLAKE_SEQUENCE_KEY,
                    value='0',
                    group='internal',
                    management_level=SystemConfigManagementLevelEnum.INTERNAL.value,
                    describe='系统ID发号高水位：必须备份，不可清空或单独回退',
                ),
            ], ignore_conflicts=True)
        for _ in range(64):
            previous = sequences.values_list('value', flat=True).get()
            if not isinstance(previous, str) or not previous.isascii() or not previous.isdecimal():
                raise SystemError(SYSTEM_ID_SEQUENCE_EXHAUSTED)
            current = max(0, time.time_ns() // 1_000_000 - 1288834974657) * 4096
            start = max(int(previous), current)
            end = start + 256
            if end > (1 << 53):
                raise SystemError(SYSTEM_ID_SEQUENCE_EXHAUSTED)
            # 条件更新是原子的，MySQL/SQLite 均不依赖进程锁或缓存 TTL。
            if sequences.filter(value=previous).update(value=str(end)):
                return start, end
        raise SystemError(SYSTEM_ID_SEQUENCE_EXHAUSTED)
    finally:
        connection.close()
