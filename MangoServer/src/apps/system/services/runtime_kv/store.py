"""独立的 MySQL KV 能力；不替换 Django 缓存或 CacheData。"""

from datetime import timedelta, timezone as datetime_timezone
from contextlib import contextmanager
import json
import re
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, IntegrityError, InterfaceError, OperationalError, connections, transaction
from django.utils import timezone
from pydantic import ValidationError

from src.apps.system.constants import RUNTIME_KV_POLICIES
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum, RuntimeKVValueTypeEnum
from src.apps.system.exceptions import (
    SYSTEM_RUNTIME_KV_CORRUPT, SYSTEM_RUNTIME_KV_INVALID, SYSTEM_RUNTIME_KV_OVERFLOW,
    SYSTEM_RUNTIME_KV_TYPE_MISMATCH, SystemError,
)
from src.apps.system.models import RuntimeKVEntry
from src.apps.system.schemas.runtime_kv import RuntimeKVEntrySchema, RuntimeKVValueSchema, RuntimeKVWriteSchema
from src.apps.system.selectors.runtime_kv import RuntimeKVSelector


_DEFAULT_TTL = object()


class RuntimeKV:
    @staticmethod
    def namespace(namespace):
        if not isinstance(namespace, RuntimeKVNamespaceEnum):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        return RuntimeKVStore(namespace)


class RuntimeKVStore:
    def __init__(self, namespace):
        if not isinstance(namespace, RuntimeKVNamespaceEnum):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        self.name = namespace.value
        self.policy = dict(RUNTIME_KV_POLICIES[self.name])
        self.using = 'default'

    def independent(self):
        """安全配额不能跟随外层业务事务回滚；独立提交但仍使用同一平台数据库。"""
        alias = 'runtime_kv_control'
        if alias not in connections.databases:
            config = dict(connections['default'].settings_dict)
            options = dict(config.get('OPTIONS') or {})
            options.update(connect_timeout=3, read_timeout=3, write_timeout=3)
            init = str(options.get('init_command') or '').strip().rstrip(';')
            if init and not init.upper().startswith('SET '):
                raise ImproperlyConfigured('RuntimeKV 独立连接只接受 SET 初始化配置')
            options['init_command'] = ('SET ' + init[4:] + ', ' if init else 'SET ') + 'innodb_lock_wait_timeout=1'
            config['OPTIONS'] = options
            connections.databases[alias] = config
        store = RuntimeKVStore(RuntimeKVNamespaceEnum(self.name))
        store.using = alias
        return store

    @contextmanager
    def control_connection(self):
        """只在控制事务开始前探活；事务开始后断连不自动重放，提交结果仍需对账。"""
        connection = connections[self.using]
        if self.using != 'runtime_kv_control' or connection.in_atomic_block:
            raise ImproperlyConfigured('配额控制连接必须在独立事务之外准备')
        try:
            reconnect_started = None
            if connection.connection is not None and not self.control_connection_usable(connection):
                reconnect_started = time.monotonic()
                connection.close()
            connection.ensure_connection()
            if reconnect_started is not None:
                from src.common.logging import log
                log.system.debug(
                    'event=datasource_control_reconnected namespace=%s duration_ms=%.2f',
                    self.name, (time.monotonic() - reconnect_started) * 1000,
                )
            yield
        except Exception:
            # 也覆盖进入 atomic/set_autocommit 时断连；下次调用可重新连接，但不重放本次操作。
            if not connection.in_atomic_block and connection.errors_occurred:
                try:
                    connection.close()
                except Exception:
                    # Django close 在 finally 中清除旧句柄；关闭错误不能覆盖原事务错误。
                    from src.common.logging import log
                    log.system.debug('event=datasource_control_discard_failed namespace=%s', self.name)
            raise

    @staticmethod
    def control_connection_usable(connection):
        # Django MySQL 的 is_usable()/驱动 ping 可能隐式重连，绕过 Django 会话初始化。
        try:
            with connection.wrap_database_errors:
                with connection.connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
            return True
        except (DatabaseError, InterfaceError):
            return False

    def confirm_control_rollback(self):
        """仅在控制事务退出后确认回滚；不重连结果未知的旧会话。"""
        connection = connections[self.using]
        if (self.using != 'runtime_kv_control' or connection.in_atomic_block
                or connection.connection is None or connection.closed_in_transaction):
            raise ImproperlyConfigured('配额控制事务回滚状态无法确认，禁止重试')
        # 1205 默认只回滚失败语句，必须收到整个事务 ROLLBACK 的确认再重试。
        connection.rollback()

    @staticmethod
    def _key(key):
        if not isinstance(key, str) or not re.fullmatch(r'[!-~]{1,192}', key):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        return key

    def _keys(self, keys):
        if not isinstance(keys, (list, tuple)) or len(keys) > 100:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        return sorted(set(self._key(key) for key in keys))

    def _ttl(self, ttl):
        if ttl is _DEFAULT_TTL:
            ttl = self.policy['ttl']
        if ttl is None:
            if not self.policy['persistent']:
                raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        elif type(ttl) is not int or not -2147483648 <= ttl <= 2147483647:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        return ttl

    def _value(self, value):
        try:
            payload = RuntimeKVValueSchema.model_validate({'data': value}, strict=True)
            encoded = json.dumps(payload.model_dump(), ensure_ascii=False, allow_nan=False,
                                 separators=(',', ':')).encode('utf-8')
        except (ValidationError, TypeError, ValueError, RecursionError, UnicodeError) as error:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID) from error
        if len(encoded) > self.policy['max_bytes']:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)

        def depth(item, level=0):
            if level > 16:
                raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
            if type(item) is int and not -(1 << 63) <= item < (1 << 63):
                raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
            if isinstance(item, dict):
                for child in item.values():
                    depth(child, level + 1)
            elif isinstance(item, list):
                for child in item:
                    depth(child, level + 1)

        depth(payload.data)
        return json.loads(encoded)

    def _now(self):
        connection = connections[self.using]
        if connection.vendor != 'mysql':
            raise ImproperlyConfigured('RuntimeKV 运行存储只支持 MySQL')
        with connection.cursor() as cursor:
            cursor.execute('SELECT CURRENT_TIMESTAMP(6)')
            now = cursor.fetchone()[0]
        if settings.USE_TZ and timezone.is_naive(now):
            now = timezone.make_aware(now, connection.timezone)
        return now

    def server_time(self):
        with connections[self.using].cursor() as cursor:
            cursor.execute('SELECT UTC_TIMESTAMP(6)')
            value = cursor.fetchone()[0]
        return timezone.make_aware(value, datetime_timezone.utc) if timezone.is_naive(value) else value

    def _transaction(self, operation):
        outer = connections[self.using].in_atomic_block
        for attempt in range(3):
            try:
                with transaction.atomic(using=self.using):
                    return operation()
            except (IntegrityError, OperationalError) as error:
                code = error.args[0] if error.args else None
                # 外层事务的死锁/锁等待由事务所有者处理；唯一冲突在保存点回滚后重读。
                retry = (isinstance(error, IntegrityError) and code == 1062) or (
                    not outer and isinstance(error, OperationalError) and code in {1205, 1213})
                if not retry or attempt == 2:
                    raise
                if not outer:
                    time.sleep(0.02 * (attempt + 1))

    def _locked(self, key):
        return RuntimeKVEntry.objects.using(self.using).select_for_update().filter(
            namespace=self.name, key=key,
        ).first()

    @staticmethod
    def _live(row, now):
        return row is not None and (row.expires_at is None or row.expires_at > now)

    @staticmethod
    def _version(row):
        return f'{row.pk}:{row.revision}'

    @staticmethod
    def _check_version(version):
        if not isinstance(version, str) or len(version) > 64 or not re.fullmatch(r'[1-9][0-9]*:[1-9][0-9]*', version):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)

    def _save(self, row, key, value, value_type, expires_at):
        if row is None:
            row = RuntimeKVEntry.objects.using(self.using).create(
                namespace=self.name, key=key, value=value, value_type=value_type, expires_at=expires_at,
            )
        else:
            row.value, row.value_type, row.expires_at = value, value_type, expires_at
            row.revision += 1
            row.save(using=self.using, update_fields=['value', 'value_type', 'expires_at', 'revision', 'update_time'])
        return self._version(row)

    @staticmethod
    def _expiry(now, ttl):
        return None if ttl is None else now + timedelta(seconds=ttl)

    @staticmethod
    def _payload(row):
        try:
            value = RuntimeKVValueSchema.model_validate(row.value, strict=True).data
        except ValidationError as error:
            raise SystemError(SYSTEM_RUNTIME_KV_CORRUPT) from error
        if row.value_type not in {kind.value for kind in RuntimeKVValueTypeEnum} or (
            row.value_type == RuntimeKVValueTypeEnum.COUNTER.value and (
                type(value) is not int or not -(1 << 63) <= value < (1 << 63))
        ):
            raise SystemError(SYSTEM_RUNTIME_KV_CORRUPT)
        return value

    def get_entry(self, key):
        key = self._key(key)
        row = RuntimeKVSelector.entries(self.name, [key], self.using).first()
        if row is None:
            return RuntimeKVEntrySchema(found=False)
        ttl = -1 if row.expires_at is None else max(0, int((row.expires_at - row.kv_now).total_seconds()))
        return RuntimeKVEntrySchema(found=True, value=self._payload(row), value_type=row.value_type,
                                    version=self._version(row), expires_at=row.expires_at, ttl=ttl)

    def get(self, key, default=None):
        entry = self.get_entry(key)
        return entry.value if entry.found else default

    def exists(self, key):
        return RuntimeKVSelector.entries(self.name, [self._key(key)], self.using).exists()

    def get_many(self, keys):
        keys = self._keys(keys)
        return {row.key: self._payload(row) for row in RuntimeKVSelector.entries(self.name, keys, self.using)}

    def _put(self, key, value, ttl, expected_version=None, absent=False, now=None):
        row = self._locked(key)
        # 单键操作在拿到行锁后取时间，不能按锁等待前的时间判断是否过期。
        now = self._now() if now is None else now
        live = self._live(row, now)
        if absent and live:
            return False, None
        if expected_version is not None and (not live or self._version(row) != expected_version):
            return False, None
        if ttl is not None and ttl <= 0:
            if row is not None:
                row.delete(using=self.using)
            return True, None
        version = self._save(row, key, value, RuntimeKVValueTypeEnum.JSON.value, self._expiry(now, ttl))
        return True, version

    def set(self, key, value, ttl=_DEFAULT_TTL):
        key, value, ttl = self._key(key), self._value(value), self._ttl(ttl)
        return self._transaction(lambda: self._put(key, value, ttl))[1]

    def set_if_absent(self, key, value, ttl=_DEFAULT_TTL):
        key, value, ttl = self._key(key), self._value(value), self._ttl(ttl)
        if ttl is not None and ttl <= 0:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        return self._transaction(lambda: self._put(key, value, ttl, absent=True))

    def compare_and_set(self, key, expected_version, value, ttl=_DEFAULT_TTL):
        self._check_version(expected_version)
        key, value, ttl = self._key(key), self._value(value), self._ttl(ttl)
        return self._transaction(lambda: self._put(key, value, ttl, expected_version=expected_version))

    def atomic_update(self, key, transform, *, ttl=_DEFAULT_TTL, utc_clock=False):
        """短事务内变换有界 JSON；transform 不得休眠或访问外部服务。"""
        key, ttl = self._key(key), self._ttl(ttl)

        def operation():
            row = self._locked(key)
            now = self._now()
            current = self._payload(row) if self._live(row, now) else None
            value, result = transform(current, self.server_time() if utc_clock else now)
            self._save(row, key, self._value(value), RuntimeKVValueTypeEnum.JSON.value, self._expiry(now, ttl))
            return result

        return self._transaction(operation)

    def set_many(self, items):
        if not isinstance(items, list) or len(items) > 100:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        prepared = []
        total = 0
        for item in items:
            try:
                validated = RuntimeKVWriteSchema.model_validate(item, strict=True)
            except ValidationError as error:
                raise SystemError(SYSTEM_RUNTIME_KV_INVALID) from error
            value = self._value(validated.value)
            ttl = self._ttl(validated.ttl if 'ttl' in validated.model_fields_set else _DEFAULT_TTL)
            total += len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
            prepared.append((validated.key, value, ttl))
        if total > 1024 * 1024 or len({item[0] for item in prepared}) != len(prepared):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        ordered = sorted(prepared, key=lambda item: item[0])

        def operation():
            for key, _, _ in ordered:
                self._locked(key)
            now = self._now()
            return {key: self._put(key, value, ttl, now=now)[1] for key, value, ttl in ordered}

        return self._transaction(operation)

    def delete_many(self, keys):
        keys = self._keys(keys)

        def operation():
            rows = list(RuntimeKVEntry.objects.using(self.using).select_for_update().filter(
                namespace=self.name, key__in=keys,
            ).order_by('key'))
            return RuntimeKVEntry.objects.using(self.using).filter(pk__in=[row.pk for row in rows]).delete()[0]

        return self._transaction(operation)

    def delete(self, key):
        return self.delete_many([key])

    def delete_if_version(self, key, expected_version):
        key = self._key(key)
        self._check_version(expected_version)

        def operation():
            row = self._locked(key)
            if not self._live(row, self._now()) or self._version(row) != expected_version:
                return False
            row.delete(using=self.using)
            return True

        return self._transaction(operation)

    def ttl(self, key):
        row = RuntimeKVSelector.entries(self.name, [self._key(key)], self.using).only('expires_at').first()
        if row is None:
            return -2
        return -1 if row.expires_at is None else max(0, int((row.expires_at - row.kv_now).total_seconds()))

    def expire(self, key, ttl):
        key, ttl = self._key(key), self._ttl(ttl)

        def operation():
            row = self._locked(key)
            now = self._now()
            if not self._live(row, now):
                return False
            if ttl is not None and ttl <= 0:
                row.delete(using=self.using)
            else:
                self._save(row, key, row.value, row.value_type, self._expiry(now, ttl))
            return True

        return self._transaction(operation)

    def persist(self, key):
        return self.expire(key, None)

    @staticmethod
    def _integer(value):
        if type(value) is not int:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        if not -(1 << 63) <= value < (1 << 63):
            raise SystemError(SYSTEM_RUNTIME_KV_OVERFLOW)
        return value

    def increment(self, key, delta=1, initial=0, ttl=_DEFAULT_TTL):
        key, ttl = self._key(key), self._ttl(ttl)
        self._integer(delta)
        self._integer(initial)
        if ttl is not None and ttl <= 0:
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)

        def operation():
            row = self._locked(key)
            now = self._now()
            if self._live(row, now):
                if row.value_type != RuntimeKVValueTypeEnum.COUNTER.value:
                    raise SystemError(SYSTEM_RUNTIME_KV_TYPE_MISMATCH)
                current, expires = self._payload(row), row.expires_at
            else:
                current, expires = initial, self._expiry(now, ttl)
            value = self._integer(current + delta)
            self._save(row, key, {'data': value}, RuntimeKVValueTypeEnum.COUNTER.value, expires)
            return value

        return self._transaction(operation)

    def decrement(self, key, delta=1, initial=0, ttl=_DEFAULT_TTL):
        self._integer(delta)
        # -MIN_INT 超出单次 delta 范围，明确拒绝而非产生不受限整数。
        return self.increment(key, self._integer(-delta), initial, ttl)

    def scan(self, prefix='', after_id=0, page_size=100):
        if prefix:
            self._key(prefix)
        if not isinstance(prefix, str) or type(after_id) is not int or after_id < 0 or (
            type(page_size) is not int or not 1 <= page_size <= 100
        ):
            raise SystemError(SYSTEM_RUNTIME_KV_INVALID)
        rows = RuntimeKVSelector.scan(self.name, prefix, after_id, page_size, self.using)
        items = [{'id': row.pk, 'key': row.key, 'value_type': row.value_type, 'version': self._version(row),
                  'expires_at': row.expires_at, 'update_time': row.update_time} for row in rows]
        return {'items': items, 'next_cursor': items[-1]['id'] if len(items) == page_size else None}

    def cleanup_expired(self, batch_size=500, max_batches=20, max_seconds=10):
        from src.apps.system.services.runtime_kv.cleanup import RuntimeKVCleanupService

        return RuntimeKVCleanupService.cleanup_expired(batch_size, max_batches, max_seconds,
                                                      RuntimeKVNamespaceEnum(self.name))
