"""Confirmation contracts without environment database writes."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier, Lock
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.db import OperationalError
from django.test import SimpleTestCase, override_settings

from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.exceptions import SystemError
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.runtime_kv.store import RuntimeKVStore
from src.interfaces.mcp import common


class ConfirmationStoreFixture:
    def __init__(self):
        self.rows = {}
        self.revision = 0
        self.now = 0
        self.lock = Lock()
        self.read_barrier = None

    def set(self, key, value, ttl):
        with self.lock:
            self.revision += 1
            version = f'1:{self.revision}'
            self.rows[key] = (deepcopy(value), version, self.now + ttl)
            return version

    def get_entry(self, key):
        with self.lock:
            row = self.rows.get(key)
            found = row is not None and row[2] > self.now
            result = SimpleNamespace(
                found=found,
                value=deepcopy(row[0]) if found else None,
                version=row[1] if found else None,
            )
        if self.read_barrier is not None:
            self.read_barrier.wait(timeout=5)
        return result

    def delete_if_version(self, key, version):
        with self.lock:
            row = self.rows.get(key)
            if row is None or row[1] != version or row[2] <= self.now:
                return False
            del self.rows[key]
            return True


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class DangerousConfirmationTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.store = ConfirmationStoreFixture()
        namespace = patch.object(RuntimeKV, 'namespace', return_value=self.store)
        self.namespace = namespace.start()
        self.addCleanup(namespace.stop)
        user = patch.object(common, 'current_user', return_value=SimpleNamespace(id=7))
        self.current_user = user.start()
        self.addCleanup(user.stop)

    @staticmethod
    def issue(**kwargs):
        return common.create_dangerous_action_preview(
            'execute_factory', '42:arguments-digest', 'Execute isolated fixture',
            {'can_execute': True, 'sensitive_source': 'must-not-be-persisted'}, **kwargs,
        )

    @staticmethod
    def consume(preview, **kwargs):
        values = {
            'action': preview['action'], 'target_id': preview['target_id'],
            'preview_token': preview['preview_token'], 'confirm_text': preview['confirm_text'],
        }
        values.update(kwargs)
        return common.validate_dangerous_action_confirmation(**values)

    def test_confirmation_survives_ordinary_cache_eviction(self):
        preview = self.issue()
        cache.clear()
        self.assertIsNone(self.consume(preview))

    def test_concurrent_consumers_only_one_can_execute(self):
        preview = self.issue()
        barrier = Barrier(2)
        self.store.read_barrier = barrier
        original_get = cache.get

        def read_then_wait(*args, **kwargs):
            value = original_get(*args, **kwargs)
            barrier.wait(timeout=5)
            return value

        legacy_cache = SimpleNamespace(get=read_then_wait, delete=cache.delete)
        with patch.object(common, 'cache', legacy_cache, create=True), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.consume(preview), range(2)))
        self.assertEqual(sum(item is None for item in results), 1)
        rejected = next(item for item in results if item is not None)
        self.assertEqual(rejected['error_code'], 'PREVIEW_EXPIRED')

    def test_failed_storage_write_does_not_issue_confirmation(self):
        with patch.object(cache, 'set', return_value=False), \
                patch.object(self.store, 'set', side_effect=OperationalError('fixture storage unavailable')):
            with self.assertRaises(OperationalError):
                self.issue()

    def test_wrong_text_does_not_consume_confirmation(self):
        preview = self.issue()
        self.assertEqual(self.consume(preview, confirm_text='wrong')['error_code'], 'CONFIRM_TEXT_MISMATCH')
        self.assertIsNone(self.consume(preview))
        self.assertEqual(self.consume(preview)['error_code'], 'PREVIEW_EXPIRED')

    def test_identity_action_target_and_token_are_isolated(self):
        preview = self.issue()
        self.current_user.return_value = SimpleNamespace(id=8)
        self.assertEqual(self.consume(preview)['error_code'], 'PREVIEW_EXPIRED')
        self.current_user.return_value = SimpleNamespace(id=7)
        for overrides in ({'action': 'delete_factory'}, {'target_id': '43'}, {'preview_token': 'other'}):
            with self.subTest(overrides=overrides):
                self.assertEqual(self.consume(preview, **overrides)['error_code'], 'PREVIEW_EXPIRED')
        self.assertIsNone(self.consume(preview))

    def test_expiry_is_enforced_without_consuming_other_tokens(self):
        expired = self.issue(ttl_seconds=1)
        live = self.issue(ttl_seconds=600)
        self.store.now = 1
        result = self.consume(expired)
        self.assertIsNotNone(result)
        self.assertEqual(result['error_code'], 'PREVIEW_EXPIRED')
        self.assertIsNone(self.consume(live))

    def test_missing_confirmation_never_reads_storage(self):
        preview = self.issue()
        with patch.object(self.store, 'get_entry') as read:
            for overrides in ({'preview_token': None}, {'confirm_text': ''}):
                self.assertEqual(self.consume(preview, **overrides)['error_code'], 'PREVIEW_REQUIRED')
        read.assert_not_called()

    def test_stored_binding_is_minimal_and_key_does_not_contain_token(self):
        preview = self.issue()
        self.assertEqual(len(self.store.rows), 1)
        key, (payload, _, _) = next(iter(self.store.rows.items()))
        self.assertNotIn(preview['preview_token'], key)
        self.assertLessEqual(len(key), 192)
        self.assertEqual(set(payload), {'user_id', 'action', 'target_id', 'confirm_text'})
        self.assertEqual(payload['user_id'], 7)
        self.assertEqual(preview['impact']['sensitive_source'], 'must-not-be-persisted')

    def test_response_contract_and_default_ttl_are_preserved(self):
        preview = self.issue()
        self.assertEqual(set(preview), {
            'action', 'target_id', 'operator_user_id', 'impact', 'preview_token',
            'confirm_text', 'expires_in_seconds', 'next_step',
        })
        self.assertEqual(preview['expires_in_seconds'], 600)
        self.assertEqual(preview['operator_user_id'], 7)

    def test_namespace_policy_is_sensitive_bounded_and_nonpersistent(self):
        self.issue()
        self.namespace.assert_called_with(RuntimeKVNamespaceEnum.MCP_CONFIRMATION)
        store = RuntimeKVStore(RuntimeKVNamespaceEnum.MCP_CONFIRMATION)
        self.assertEqual(store.policy, {'ttl': 600, 'persistent': False, 'sensitive': True, 'max_bytes': 8192})
        with self.assertRaises(SystemError):
            store._ttl(None)
        with self.assertRaises(SystemError):
            store._value('x' * 8192)

    def test_invalid_ttl_is_rejected_before_storage(self):
        with patch.object(self.store, 'set') as write:
            for ttl in (0, -1, True, None, 1.5, 2147483648):
                with self.subTest(ttl=ttl), self.assertRaises(SystemError):
                    self.issue(ttl_seconds=ttl)
        write.assert_not_called()

    def test_expiry_between_read_and_consume_is_rejected(self):
        preview = self.issue(ttl_seconds=1)
        original_get = self.store.get_entry

        def expire_after_read(key):
            entry = original_get(key)
            self.store.now = 1
            return entry

        with patch.object(self.store, 'get_entry', side_effect=expire_after_read):
            self.assertEqual(self.consume(preview)['error_code'], 'PREVIEW_EXPIRED')

    def test_replaced_version_is_not_consumed(self):
        preview = self.issue()
        original_get = self.store.get_entry

        def replace_after_read(key):
            entry = original_get(key)
            self.store.set(key, entry.value, ttl=600)
            return entry

        with patch.object(self.store, 'get_entry', side_effect=replace_after_read):
            self.assertEqual(self.consume(preview)['error_code'], 'PREVIEW_EXPIRED')
        self.assertEqual(len(self.store.rows), 1)

    def test_corrupt_payload_is_not_accepted_or_consumed(self):
        preview = self.issue()
        key, (payload, version, expiry) = next(iter(self.store.rows.items()))
        for value in ({}, dict(payload, user_id='7'), dict(payload, unexpected='field')):
            self.store.rows[key] = (value, version, expiry)
            with self.subTest(value=value), self.assertRaises(SystemError):
                self.consume(preview)
            self.assertIn(key, self.store.rows)

    def test_payload_scope_mismatch_is_not_consumed(self):
        preview = self.issue()
        key, (payload, version, expiry) = next(iter(self.store.rows.items()))
        for changes in ({'user_id': 8}, {'action': 'other'}, {'target_id': 'other'}):
            self.store.rows[key] = (dict(payload, **changes), version, expiry)
            self.assertEqual(self.consume(preview)['error_code'], 'PREVIEW_EXPIRED')
            self.assertIn(key, self.store.rows)

    def test_storage_read_and_consume_errors_do_not_fall_back(self):
        preview = self.issue()
        for method in ('get_entry', 'delete_if_version'):
            with patch.object(self.store, method, side_effect=OperationalError('fixture failure')):
                with self.subTest(method=method), self.assertRaises(OperationalError):
                    self.consume(preview)
        self.assertIsNone(self.consume(preview))

    def test_unknown_consumption_result_is_not_accepted(self):
        preview = self.issue()
        for result in (None, 'accepted', object()):
            with patch.object(common.McpConfirmationService, 'consume', return_value=result):
                self.assertEqual(self.consume(preview)['error_code'], 'PREVIEW_EXPIRED')

    def test_confirmation_logs_do_not_contain_secrets_or_payloads(self):
        with self.assertLogs('src.apps.system.services.coordination.mcp_confirmation', level='INFO') as captured:
            preview = self.issue()
            self.assertIsNone(self.consume(preview))
        logged = '\n'.join(captured.output)
        for value in (preview['preview_token'], preview['confirm_text'], preview['impact']['sensitive_source']):
            self.assertNotIn(value, logged)

    def test_isolated_store_roundtrip_across_processes(self):
        # SQLite is a disposable fixture, not proof of MySQL row-lock semantics.
        script = r'''
import json, os, sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
os.environ['DJANGO_ENV'] = 'dev'
os.environ['DJANGO_SETTINGS_MODULE'] = 'src.settings'
from django.conf import settings
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': sys.argv[1]}}
settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
import django
django.setup()
from django.db import connection
from src.apps.system.models import RuntimeKVEntry
from src.apps.system.services.runtime_kv.store import RuntimeKVStore
from src.interfaces.mcp import common
connection.ensure_connection()
connection.connection.create_collation('utf8mb4_bin', lambda a, b: (a > b) - (a < b))
if sys.argv[2] == 'issue':
    with connection.schema_editor() as editor:
        editor.create_model(RuntimeKVEntry)
with patch.object(common, 'current_user', return_value=SimpleNamespace(id=7)), \
        patch.object(RuntimeKVStore, '_now', side_effect=datetime.utcnow):
    if sys.argv[2] == 'issue':
        result = common.create_dangerous_action_preview('fixture', 42, 'Confirm fixture', {})
    else:
        preview = json.load(sys.stdin)
        result = common.validate_dangerous_action_confirmation(
            preview['action'], preview['target_id'], preview['preview_token'], preview['confirm_text'])
print(json.dumps(result))
'''
        root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as directory:
            database = str(Path(directory) / 'confirmation.sqlite3')

            def run(mode, preview=None):
                result = subprocess.run(
                    [sys.executable, '-c', script, database, mode],
                    input=json.dumps(preview) if preview else None,
                    cwd=root, env=dict(os.environ), text=True, capture_output=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout.splitlines()[-1])

            preview = run('issue')
            self.assertIsNone(run('consume', preview))
            self.assertEqual(run('consume', preview)['error_code'], 'PREVIEW_EXPIRED')
