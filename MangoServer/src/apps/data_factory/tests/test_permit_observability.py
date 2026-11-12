"""故障注入只使用隔离控制存储，不写共享业务数据源。"""
import copy
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase

from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum, DatasourceQueueLaneEnum
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy, DatasourceTypeBudget
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService as Recovery
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit
from src.apps.data_factory.tests.test_datasource_performance import AtomicMemoryStore


class PermitRetentionAndSchedulerTests(SimpleTestCase):
    def test_scheduled_monitor_persists_pagination_and_requests_only_confirmed_recovery(self):
        store = SimpleNamespace(control_connection=lambda: nullcontext(),
            get=Mock(return_value={'after_id': 100}), set=Mock())
        with patch.object(Governor, 'store', return_value=store), \
                patch.object(Recovery, 'monitor', return_value={
                    'groups': [{'suspect_count': 2, 'connection_waiting': True}], 'errors': [],
                    'recovered_count': 1, 'next_cursor': 200}) as monitor:
            result = Recovery.scheduled_monitor()
        monitor.assert_called_once_with(after_id=100, recover=True)
        store.set.assert_called_once_with('monitor:cursor', {'after_id': 200}, ttl=None)
        self.assertEqual(result['datasource_suspect_permits'], 2)
        self.assertEqual(result['datasource_reconciled_permits'], 1)

    def test_retention_preserves_running_unresolved_and_referenced_audit_records(self):
        with patch.object(Recovery, 'referenced_audit_ids', return_value={77}), \
                patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionRecord.objects') as records:
            records.filter.return_value.exclude.return_value.exclude.return_value.exclude.return_value.delete.return_value = (3, {})
            self.assertEqual(Audit.cleanup_expired('cutoff'), 3)
        records.filter.assert_called_once_with(create_time__lt='cutoff')
        records.filter.return_value.exclude.assert_called_once_with(status='running')
        records.filter.return_value.exclude.return_value.exclude.assert_called_once_with(
            source_detail__outcome_unknown=True, source_detail__outcome_resolution__isnull=True)
        records.filter.return_value.exclude.return_value.exclude.return_value.exclude.assert_called_once_with(id__in={77})

    def test_retention_does_not_delete_when_permit_evidence_cannot_be_read(self):
        with patch.object(Recovery, 'referenced_audit_ids', side_effect=OperationalError(2013, 'offline')), \
                patch('src.apps.data_factory.services.sql.sql_execution_audit.SqlExecutionRecord.objects') as records:
            with self.assertRaises(OperationalError):
                Audit.cleanup_expired('cutoff')
        records.filter.assert_not_called()

    def test_monitor_failure_does_not_prevent_cleanup_and_todo_reconciliation(self):
        from src.processes.scheduler.system_jobs import SchedulerSystemJobService
        with patch.object(Audit, 'recover_stale', return_value={}), \
                patch('src.apps.data_factory.services.recovery.execution_recovery.DataFactoryExecutionRecovery.recover',
                      return_value={'cleanup_checked': 1}) as cleanup, \
                patch('src.apps.task_center.services.workbench.todo.WorkbenchTodoService.reconcile_non_auth_todos',
                      return_value={'todos_checked': 1}) as todos, \
                patch.object(Recovery, 'scheduled_monitor', side_effect=OperationalError(2013, 'offline')):
            result = SchedulerSystemJobService.reconcile_workbench_todos.__wrapped__(SchedulerSystemJobService)
        cleanup.assert_called_once()
        todos.assert_called_once()
        self.assertTrue(result['datasource_monitor_failed'])
        self.assertEqual(result['cleanup_checked'], 1)
