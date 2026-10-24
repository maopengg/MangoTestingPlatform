from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.services.connection_query import DataSourceConnectionQueryService
from src.apps.test_center.exceptions import TestCenterError


class ConnectionQueryTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        for method in ['start', 'finish_success', 'finish_failure']:
            patcher = patch('src.apps.data_factory.services.connection_query.SqlExecutionAuditService.' + method)
            setattr(self, 'audit_' + method, patcher.start())
            self.addCleanup(patcher.stop)

    def test_read_only_statements(self):
        for sql in ['SELECT 1 LIMIT 1', 'SELECT 1 LIMIT 1;',
                    'WITH picked_rows AS (SELECT 1) SELECT * FROM picked_rows LIMIT 20',
                    "SELECT 'DELETE INTO UPDATE' LIMIT 2", '-- comment\nSELECT 1 LIMIT 1',
                    'SELECT * FROM orders LIMIT 200 OFFSET 10', 'SELECT * FROM orders LIMIT 10, 200']:
            with self.subTest(sql=sql):
                self.assertTrue(DataSourceConnectionQueryService.validate_sql(sql))

    def test_requires_outer_numeric_quantity(self):
        for sql in ['SELECT * FROM orders', 'SELECT COUNT(*) FROM orders',
                    'SELECT * FROM (SELECT * FROM orders LIMIT 20) picked',
                    'SELECT * FROM orders LIMIT ALL', 'SELECT * FROM orders LIMIT 201',
                    'SELECT * FROM orders LIMIT 0', 'SELECT * FROM orders LIMIT -1',
                    'SELECT * FROM orders LIMIT :quantity', "SELECT 'LIMIT 20'", 'SHOW TABLES']:
            with self.subTest(sql=sql), self.assertRaises(TestCenterError):
                DataSourceConnectionQueryService.validate_sql(sql)

    def test_rejects_writes_multiple_statements_and_side_effects(self):
        for sql in ['', 'DELETE FROM orders', 'UPDATE orders SET id=1',
                    'SELECT 1; DELETE FROM orders', 'SELECT * FROM orders FOR UPDATE',
                    "SELECT 1 INTO OUTFILE '/tmp/output'", 'EXPLAIN ANALYZE DELETE FROM orders',
                    'WITH picked_rows AS (DELETE FROM orders RETURNING *) SELECT * FROM picked_rows',
                    'WITH picked_rows AS (SELECT 1) UPDATE orders SET id=1']:
            with self.subTest(sql=sql), self.assertRaises(TestCenterError):
                DataSourceConnectionQueryService.validate_sql(sql)

    @patch('src.apps.data_factory.services.connection_query.DataFactoryDatasource.create_engine')
    @patch('src.apps.data_factory.services.connection_query.DatasourceTargetService.build')
    @patch('src.apps.data_factory.services.connection_query.DataSourceDiscoveryService.require_relational')
    @patch('src.apps.data_factory.services.connection_query.DataSourceDiscoveryService.get_database')
    def test_executes_in_read_only_transaction_with_limit_and_disposal(self, get_source, require_relational,
                                                                       build_target, create_engine):
        connection = create_engine.return_value.connect.return_value.__enter__.return_value
        result = MagicMock()
        result.keys.return_value = ['id']
        result.fetchmany.return_value = [(i,) for i in range(201)]
        connection.exec_driver_sql.return_value = result

        response = DataSourceConnectionQueryService.query(1, 'sample', 'SELECT id FROM orders LIMIT 200')

        build_target.assert_called_once_with(get_source.return_value, database_name='sample')
        self.assertEqual(connection.exec_driver_sql.call_args_list[0].args, ('SET TRANSACTION READ ONLY',))
        self.assertEqual(response['row_count'], 200)
        self.assertTrue(response['truncated'])
        self.assertEqual(len(response['rows']), 200)
        connection.rollback.assert_called_once()
        create_engine.return_value.dispose.assert_called_once()
        self.audit_start.assert_not_called()
        self.assertNotIn('sql_execution_id', response)

    @patch('src.apps.data_factory.services.connection_query.DataFactoryDatasource.create_engine')
    def test_invalid_sql_is_audited_without_opening_connection(self, create_engine):
        with self.assertRaises(TestCenterError):
            DataSourceConnectionQueryService.query_target(
                MagicMock(), 'DROP TABLE orders', binding=MagicMock(), project_product_id=3, test_env=0)
        create_engine.assert_not_called()
        self.audit_start.assert_called_once()
        self.audit_finish_failure.assert_called_once()

    @patch('src.apps.data_factory.services.connection_query.DataFactoryDatasource.create_engine')
    def test_direct_rejected_query_does_not_fabricate_audit_scope(self, create_engine):
        with self.assertRaises(TestCenterError):
            DataSourceConnectionQueryService.query_target(MagicMock(), 'SELECT * FROM orders')
        create_engine.assert_not_called()
        self.audit_start.assert_not_called()

    @patch('src.apps.data_factory.services.connection_query.DataSourceConnectionQueryService.execute_target')
    def test_logical_success_retains_existing_sql_audit(self, execute_target):
        execute_target.return_value = {'rows': [[1]], 'row_count': 1}
        response = DataSourceConnectionQueryService.query_target(
            MagicMock(), 'SELECT 1 LIMIT 1', binding=MagicMock(), project_product_id=3, test_env=0)
        self.audit_start.assert_called_once()
        self.audit_finish_success.assert_called_once()
        self.assertEqual(response['sql_execution_id'], self.audit_start.return_value.record.id)

    @patch('src.apps.data_factory.services.connection_query.DataSourceConnectionQueryService.query_target')
    @patch('src.apps.data_factory.services.connection_query.DataSourceConnectionService.require_sql')
    @patch('src.apps.data_factory.services.connection_query.DatasourceTargetService.resolve')
    @patch('src.apps.data_factory.services.connection_query.DataFactoryDatasourceResolver.require_binding_permission')
    @patch('src.apps.data_factory.services.connection_query.DataFactoryDatasourceResolver.resolve_binding_by_env')
    def test_logical_query_uses_the_same_executor_after_permission_check(self, resolve_binding, require_permission,
                                                                         resolve_target, require_sql, query_target):
        DataSourceConnectionQueryService.query_binding(2, 3, 0, 'SELECT 1 LIMIT 1', operator_id=4)
        require_permission.assert_called_once_with(resolve_binding.return_value, write=False)
        query_target.assert_called_once_with(resolve_target.return_value, 'SELECT 1 LIMIT 1',
                                             binding=resolve_binding.return_value, project_product_id=3,
                                             test_env=0, operator_id=4)
