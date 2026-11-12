from types import SimpleNamespace
from unittest.mock import Mock, patch
from contextlib import nullcontext

from django.test import SimpleTestCase
from pymysql.err import OperationalError, ProgrammingError
from sqlalchemy.exc import OperationalError as SqlOperationalError

from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_AUDIT_COMPLETION_FAILED
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService as Errors
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit, SqlExecutionAuditHandle


class AuditOutcomeClassificationTests(SimpleTestCase):
    def test_connection_admission_not_sent_is_known_without_hiding_partial_parent_operations(self):
        from src.apps.data_factory.exceptions import DATASOURCE_RECONCILIATION_REQUIRED
        error = DataFactoryError(DATASOURCE_RECONCILIATION_REQUIRED)
        error._datasource_not_sent = True
        self.assertFalse(self.record_error(error, sent=False).source_detail['outcome_unknown'])
        self.assertTrue(self.record_error(error, sent=True).source_detail['outcome_unknown'])

    def test_protocol_rejection_is_known_but_network_and_server_timeout_are_not(self):
        from urllib.error import HTTPError
        from redis.exceptions import ResponseError
        for error in (HTTPError('https://example.com', 409, 'conflict', {}, None),
                      ResponseError('AUTO_WRONGTYPE')):
            with self.subTest(error=type(error).__name__):
                self.assertFalse(Governor.outcome_unknown(error))
                self.assertFalse(self.record_error(error).source_detail['outcome_unknown'])
        for status in (408, 500, 504):
            error = HTTPError('https://example.com', status, 'unconfirmed', {}, None)
            self.assertFalse(Errors.confirmed_rejection(error))
            self.assertTrue(self.record_error(error).source_detail['outcome_unknown'])

    def record_error(self, error, sent=True):
        record = SimpleNamespace(id=1, request_id='AUTO_REQUEST', source_detail={},
                                 slow_threshold_ms=20000, save=Mock())
        with patch.object(Audit, 'notify_slow'):
            Audit.finish_failure(SqlExecutionAuditHandle(record, 0, statement_claimed=sent), error, 1)
        return record

    def test_mysql_server_rejections_are_known_failures_without_suspect_capture(self):
        for code in (1064, 3141, 1062, 1146, 1205, 1213, 3024):
            raw = ProgrammingError(code, 'AUTO_SERVER_REJECTION')
            wrapped = SqlOperationalError('SELECT AUTO', {}, raw)
            error = RuntimeError('AUTO_DOMAIN_WRAPPER')
            error.__cause__ = wrapped
            with self.subTest(code=code), Infrastructure.scope():
                record = self.record_error(error)
                self.assertFalse(record.source_detail['outcome_unknown'])
                self.assertFalse(Governor.outcome_unknown(error))
                self.assertFalse(Infrastructure.current())
                self.assertEqual(record.status, 'fail')

    def test_connection_errors_and_unknown_driver_errors_remain_unconfirmed(self):
        for error in (OperationalError(2006, 'AUTO_LOST'), OperationalError(2013, 'AUTO_LOST'),
                      OperationalError(2055, 'AUTO_LOST'), OperationalError(1158, 'AUTO_COMMUNICATION'),
                      TimeoutError(), RuntimeError('AUTO_UNKNOWN')):
            with self.subTest(error=type(error).__name__):
                self.assertTrue(self.record_error(error).source_detail['outcome_unknown'])
                self.assertFalse(Errors.confirmed_rejection(error))
                if isinstance(error, (OperationalError, TimeoutError)):
                    self.assertTrue(Governor.outcome_unknown(error))

    def test_postgres_sqlstate_is_not_inferred_from_operational_error_class(self):
        for state, rejected in (('42601', True), ('23505', True), ('22023', True),
                                ('08006', False), ('08007', False), ('40003', False)):
            error = RuntimeError('AUTO_DRIVER')
            error.sqlstate = state
            self.assertEqual(Errors.confirmed_rejection(error), rejected)
            self.assertEqual(self.record_error(error).source_detail['outcome_unknown'], not rejected)

    def test_commit_uncertainty_and_audit_failure_override_nested_statement_rejection(self):
        for error in (DataFactoryError(DATASOURCE_AUDIT_COMPLETION_FAILED), RuntimeError('AUTO_COMMIT')):
            error.__cause__ = ProgrammingError(1064, 'AUTO_PRIOR_STATEMENT')
            if isinstance(error, RuntimeError):
                error._datasource_outcome_unknown = True
            self.assertTrue(Governor.outcome_unknown(error))
            self.assertTrue(self.record_error(error).source_detail['outcome_unknown'])

    def test_not_sent_is_known_but_claimed_statement_does_not_inherit_that_flag(self):
        error = RuntimeError('AUTO_CONTROL_FAILURE')
        error._datasource_not_sent = True
        self.assertFalse(self.record_error(error, sent=False).source_detail['outcome_unknown'])
        self.assertTrue(self.record_error(error, sent=True).source_detail['outcome_unknown'])
