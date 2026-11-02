"""无共享库写入的参数、边界、事务测试与隔离 ORM 回归。"""

from contextlib import nullcontext
from datetime import datetime, timedelta
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import IntegrityError, OperationalError
from django.test import SimpleTestCase

from src.apps.system.constants import RUNTIME_KV_POLICIES
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum, RuntimeKVValueTypeEnum
from src.apps.system.exceptions import SystemError
from src.apps.system.models import RuntimeKVEntry
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.runtime_kv.cleanup import RuntimeKVCleanupService
from src.apps.system.services.runtime_kv.store import RuntimeKVStore


class RuntimeKVTests(SimpleTestCase):
    def setUp(self):
        self.store = RuntimeKV.namespace(RuntimeKVNamespaceEnum.API_AUTH)

    def test_namespace_is_enum_and_policies_match(self):
        self.assertEqual({item.value for item in RuntimeKVNamespaceEnum}, set(RUNTIME_KV_POLICIES))
        with self.assertRaises(SystemError):
            RuntimeKV.namespace('api_auth')
        self.assertEqual(self.store.name, 'api_auth')

    def test_schema_and_case_sensitive_unique_key(self):
        self.assertEqual(RuntimeKVEntry._meta.db_table, 'runtime_kv')
        self.assertEqual(RuntimeKVEntry._meta.constraints[0].fields, ('namespace', 'key'))
        self.assertEqual(RuntimeKVEntry._meta.get_field('key').db_collation, 'utf8mb4_bin')
        self.assertEqual(self.store._key('Config:18'), 'Config:18')
        for key in ('', 'a b', '中文', 'x' * 193, None, 1, 'a\n'):
            with self.subTest(key=key), self.assertRaises(SystemError):
                self.store._key(key)

    def test_values_are_json_cloned_and_bounded(self):
        for value in (None, False, 0, '', [], {}, {'list': [1, None, True, '中文']}):
            self.assertEqual(self.store._value(value), {'data': value})
        original = {'items': []}
        copied = self.store._value(original)
        original['items'].append(1)
        self.assertEqual(copied, {'data': {'items': []}})
        nested = None
        for _ in range(18):
            nested = [nested]
        for value in (float('inf'), float('nan'), object(), 'x' * 65536, nested, 1 << 80, {1: 'bad'}):
            with self.subTest(type=type(value).__name__), self.assertRaises(SystemError):
                self.store._value(value)

    def test_ttl_and_nonpositive_nx_validation(self):
        self.assertIsNone(self.store._ttl(None))
        self.assertEqual(self.store._ttl(0), 0)
        for ttl in (True, 1.1, '2', 1 << 40):
            with self.assertRaises(SystemError):
                self.store._ttl(ttl)
        other = RuntimeKV.namespace(RuntimeKVNamespaceEnum.REQUEST_DEDUP)
        with self.assertRaises(SystemError):
            other._ttl(None)
        with self.assertRaises(SystemError):
            other.set_if_absent('key', 1, ttl=0)

    def test_batch_rejected_before_any_transaction(self):
        with patch.object(self.store, '_transaction') as write:
            for items in ([{'key': 'x', 'value': 1}] * 2, [{'key': 'x', 'value': 1, 'extra': True}],
                          [{'key': str(n), 'value': 'x' * 60000} for n in range(18)],
                          [{'key': str(n), 'value': 1} for n in range(101)]):
                with self.assertRaises(SystemError):
                    self.store.set_many(items)
            write.assert_not_called()

    def test_unsafe_versions_are_rejected(self):
        self.store._check_version('12:3')
        for version in ('1', '0:1', '1:0', '1:2:3', None, '9' * 80):
            with self.assertRaises(SystemError):
                self.store._check_version(version)

    def test_payload_corruption_is_not_a_cache_miss(self):
        for row in (SimpleNamespace(value={}, value_type=0), SimpleNamespace(value={'data': True}, value_type=1),
                    SimpleNamespace(value={'data': 1 << 70}, value_type=1),
                    SimpleNamespace(value={'data': None}, value_type=9)):
            with self.assertRaises(SystemError):
                self.store._payload(row)

    def test_nx_cas_and_expired_rows(self):
        now = datetime(2026, 1, 1)
        row = SimpleNamespace(pk=1, revision=2, expires_at=now + timedelta(seconds=10))
        with patch.object(self.store, '_locked', return_value=row), patch.object(self.store, '_now', return_value=now), \
                patch.object(self.store, '_save', return_value='1:3') as save:
            self.assertEqual(self.store._put('key', {'data': 1}, 10, absent=True), (False, None))
            self.assertEqual(self.store._put('key', {'data': 1}, 10, expected_version='1:1'), (False, None))
            save.assert_not_called()
            self.assertEqual(self.store._put('key', {'data': 1}, 10, expected_version='1:2'), (True, '1:3'))
            row.expires_at = now
            self.assertEqual(self.store._put('key', {'data': 1}, 10, absent=True), (True, '1:3'))
            self.assertEqual(self.store._put('key', {'data': 1}, 10, expected_version='1:2'), (False, None))

    def test_lock_retries_respect_outer_transaction(self):
        connection = SimpleNamespace(in_atomic_block=False)
        with patch('src.apps.system.services.runtime_kv.store.connections', {'default': connection}), \
                patch('src.apps.system.services.runtime_kv.store.transaction.atomic', side_effect=lambda **kw: nullcontext()), \
                patch('src.apps.system.services.runtime_kv.store.time.sleep'):
            operation = MagicMock(side_effect=[OperationalError(1213, 'deadlock'), 'ok'])
            self.assertEqual(self.store._transaction(operation), 'ok')
            self.assertEqual(operation.call_count, 2)
            connection.in_atomic_block = True
            operation = MagicMock(side_effect=OperationalError(1213, 'deadlock'))
            with self.assertRaises(OperationalError):
                self.store._transaction(operation)
            self.assertEqual(operation.call_count, 1)
            operation = MagicMock(side_effect=[IntegrityError(1062, 'duplicate'), 'ok'])
            self.assertEqual(self.store._transaction(operation), 'ok')
            operation = MagicMock(side_effect=IntegrityError(1048, 'not null'))
            with self.assertRaises(IntegrityError):
                self.store._transaction(operation)
            self.assertEqual(operation.call_count, 1)

    def test_integer_bounds_and_expired_counter_initialization(self):
        for value in (True, 1.5, 1 << 63, -(1 << 63) - 1):
            with self.assertRaises(SystemError):
                self.store._integer(value)
        now = datetime(2026, 1, 1)
        expired = SimpleNamespace(value_type=0, expires_at=now)
        with patch.object(self.store, '_transaction', side_effect=lambda fn: fn()), \
                patch.object(self.store, '_locked', return_value=expired), \
                patch.object(self.store, '_now', return_value=now), patch.object(self.store, '_save') as save:
            self.assertEqual(self.store.increment('key', delta=2, initial=5, ttl=20), 7)
            self.assertEqual(save.call_args.args[-1], now + timedelta(seconds=20))

    def test_cleanup_waits_for_user_migration(self):
        fake = MagicMock()
        fake.introspection.table_names.return_value = []
        with patch('src.apps.system.services.runtime_kv.cleanup.connection', fake):
            result = RuntimeKVCleanupService.cleanup_expired()
        self.assertEqual(result['status'], 'pending_migration')
        for kwargs in ({'batch_size': 0}, {'max_batches': 21}, {'max_seconds': True}, {'namespace': 'api_auth'}):
            with self.assertRaises(SystemError):
                RuntimeKVCleanupService.cleanup_expired(**kwargs)

    def test_scan_returns_metadata_only_and_uses_namespace(self):
        row = SimpleNamespace(pk=7, key='example', value_type=0, revision=2, expires_at=None, update_time=None)
        with patch('src.apps.system.services.runtime_kv.store.RuntimeKVSelector.scan', return_value=[row]) as scan:
            result = self.store.scan(page_size=1)
        self.assertEqual(result['next_cursor'], 7)
        self.assertNotIn('value', result['items'][0])
        self.assertEqual(scan.call_args.args[0], 'api_auth')

    def test_isolated_orm_roundtrip_and_rollback(self):
        # 仅创建临时 SQLite 测试夹具，不连接环境 MySQL，也不生成或执行迁移。
        # 此测试不证明 MySQL 的行锁与并发语义，后者需专用 MySQL 验收。
        script = r'''
import os, sys
from datetime import datetime, timedelta
from unittest.mock import patch
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings'
from django.conf import settings
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': sys.argv[1]}}
settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
import django
django.setup()
from django.db import connection, transaction
from src.apps.system.models import RuntimeKVEntry
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum as NS
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.runtime_kv.store import RuntimeKVStore
from src.apps.system.exceptions import SystemError
connection.ensure_connection()
connection.connection.create_collation('utf8mb4_bin', lambda a, b: (a > b) - (a < b))
with connection.schema_editor() as editor:
    editor.create_model(RuntimeKVEntry)
store = RuntimeKV.namespace(NS.API_AUTH)
other = RuntimeKV.namespace(NS.REQUEST_DEDUP)
with patch.object(RuntimeKVStore, '_now', side_effect=datetime.utcnow):
    first = store.set('Key', None, ttl=None)
    assert store.exists('Key') and store.get_entry('Key').found and store.get('Key') is None
    assert store.ttl('Key') == -1 and not store.exists('key')
    assert not other.exists('Key')
    assert not store.set_if_absent('Key', 1)[0]
    assert store.compare_and_set('Key', first, {'ok': True})[0]
    assert not store.delete_if_version('Key', first)
    current = store.get_entry('Key').version
    assert store.delete_if_version('Key', current)
    fresh = store.set('Key', 2)
    assert fresh != first and not store.compare_and_set('Key', first, 3)[0]
    assert store.increment('count', 2, initial=5, ttl=100) == 7
    expiry = store.get_entry('count').expires_at
    assert store.decrement('count', 1, ttl=1) == 6
    assert store.get_entry('count').expires_at == expiry
    assert store.expire('count', 0) and store.ttl('count') == -2
    assert not store.expire('count', 10)
    store.set_many([{'key': 'a', 'value': []}, {'key': 'b', 'value': {'x': 2}, 'ttl': None}])
    assert store.get_many(['a', 'b', 'missing']) == {'a': [], 'b': {'x': 2}}
    assert store.ttl('b') == -1
    assert store.persist('a') and store.ttl('a') == -1
    try:
        with transaction.atomic():
            store.set('rollback', 1)
            raise RuntimeError('rollback')
    except RuntimeError:
        pass
    assert not store.exists('rollback')
    RuntimeKVEntry.objects.filter(key='Key').update(expires_at=datetime.utcnow() - timedelta(seconds=1))
    assert store.get('Key', 'expired') == 'expired' and not store.persist('Key')
    assert store.set_if_absent('Key', 'rebuilt')[0]
    assert store.delete_many(['a', 'b']) == 2 and store.delete('a') == 0
    original = store._put
    def fail_second(key, *args, **kwargs):
        if key == 'z':
            raise RuntimeError('batch failed')
        return original(key, *args, **kwargs)
    try:
        with patch.object(store, '_put', side_effect=fail_second):
            store.set_many([{'key': 'y', 'value': 1}, {'key': 'z', 'value': 2}])
    except RuntimeError:
        pass
    assert not store.exists('y') and not store.exists('z')
    try:
        store.increment('Key')
    except SystemError:
        pass
    else:
        raise AssertionError('type conflict not rejected')
    store.set('expired', 'sensitive', ttl=100)
    other.set('expired', 'other namespace', ttl=100)
    RuntimeKVEntry.objects.filter(key='expired').update(expires_at=datetime.utcnow() - timedelta(seconds=1))
    result = store.cleanup_expired(batch_size=1, max_batches=1)
    assert result['deleted_count'] == 1
    assert not RuntimeKVEntry.objects.filter(namespace=NS.API_AUTH.value, key='expired').exists()
    assert RuntimeKVEntry.objects.filter(namespace=NS.REQUEST_DEDUP.value, key='expired').exists()
    assert store.exists('Key')
print('isolated-runtime-kv-ok')
'''
        env = dict(os.environ, DJANGO_ENV='dev', FILE_STORAGE_BACKEND='local')
        with tempfile.TemporaryDirectory(prefix='runtime-kv-test-') as directory:
            result = subprocess.run([sys.executable, '-c', script, str(Path(directory) / 'fixture.db')],
                                    cwd=settings_base_dir(), env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('isolated-runtime-kv-ok', result.stdout)


def settings_base_dir():
    from django.conf import settings

    return settings.BASE_DIR
