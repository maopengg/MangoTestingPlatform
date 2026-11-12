"""真实子进程退出夹具：只使用原子内存控制库与物理关闭替身，不访问共享数据源。"""
import json
import os
import sys
import time
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch


def main():
    import django
    django.setup()
    from django.db import OperationalError
    from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
    from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
    from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
    from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore
    store = AtomicMemoryStore()
    store.now = time.time()
    target = SimpleNamespace(id=49, db_type=0, host='mysql.example.com', port=3306)
    with patch.object(Governor, 'store', return_value=store), \
            patch.object(Governor, 'policy', return_value=DatasourcePerformancePolicy()), \
            patch.object(Governor, 'configuration_guard', side_effect=lambda *args: nullcontext()):
        if '--without-close' in sys.argv:
            from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
            from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle
            target.cache_key = 'c' * 40
            cursor = Mock()
            cursor.fetchone.return_value = ('11111111-1111-1111-1111-111111111111', 123, 'AUTO_user@%')
            native = SimpleNamespace(thread_id=lambda: 123, _read_timeout=120,
                                     cursor=lambda: cursor, close=Mock())
            record = SimpleNamespace(id=77, source_detail={}, status='running')
            with patch.object(Audit, 'start', return_value=SqlExecutionAuditHandle(record, time.perf_counter())), \
                    patch.object(Audit, 'finish_success'):
                held = GovernedDbapiConnection.connect(target, lambda: native)
            print('PERMIT_RECOVERY_FIXTURE=' + json.dumps({'values': store.values}), flush=True)
            while held:
                time.sleep(1)
        permit = Governor.acquire(target)
        original = store.atomic_update
        def lost_group_reply(key, *args, **kwargs):
            if key.startswith('group:'):
                raise OperationalError(2013, 'lost control reply')
            return original(key, *args, **kwargs)
        with patch.object(store, 'atomic_update', side_effect=lost_group_reply):
            GovernedDbapiConnection(Mock(), permit).close()
        print('PERMIT_RECOVERY_FIXTURE=' + json.dumps({'values': store.values}), flush=True)
    os._exit(0)


if __name__ == '__main__':
    main()
