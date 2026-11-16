from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import StatementError

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService as Errors
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.sql.sql_driver_audit import SqlDriverAuditService
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditHandle, SqlExecutionAuditService as Audit


class SqlBindParameterOutcomeTests(SimpleTestCase):
    def test_real_sqlalchemy_missing_bind_is_never_sent_and_stays_known_through_domain_wrapper(self):
        engine = create_engine('sqlite:///:memory:')
        target = SimpleNamespace(id=7, db_type=2)
        record = SimpleNamespace(id=1, request_id='AUTO_BIND_REQUEST', source_detail={},
                                 slow_threshold_ms=20000, save=Mock())
        handle = SqlExecutionAuditHandle(record, 0)
        sent = []
        try:
            with engine.connect() as connection:
                SqlDriverAuditService.attach(engine, target)
                event.listen(engine, 'before_cursor_execute', lambda *args: sent.append(True))
                with Audit.scope(handle), Infrastructure.scope(), patch.object(Audit, 'save_completion'), \
                        patch.object(Audit, 'notify_slow'):
                    with self.assertRaises(DataFactoryError) as caught:
                        try:
                            connection.execute(text('SELECT :AUTO_REQUIRED'))
                        except StatementError as error:
                            self.assertTrue(error._datasource_operation_not_sent)
                            Errors.raise_sql_error(target, error)
                    Audit.finish_failure(handle, caught.exception, 1)
                    self.assertFalse(record.source_detail['outcome_unknown'])
                    self.assertEqual(record.status, 'fail')
                    self.assertFalse(Infrastructure.current())
                self.assertFalse(sent)
                self.assertFalse(handle.statement_claimed)
        finally:
            engine.dispose()

    def test_arbitrary_statement_error_is_not_declared_unsent(self):
        original = RuntimeError('AUTO_UNKNOWN_DRIVER')
        error = StatementError('AUTO_DRIVER', 'UPDATE example', {}, original)
        with self.assertRaises(DataFactoryError) as caught:
            Errors.raise_sql_error(SimpleNamespace(db_type=0, database_name='example'), error)
        self.assertFalse(getattr(caught.exception, '_datasource_operation_not_sent', False))
