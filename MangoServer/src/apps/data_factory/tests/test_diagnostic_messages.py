from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase

from src.apps.data_factory.exceptions import (
    DataFactoryError, DATASOURCE_GOVERNOR_UNAVAILABLE, DATASOURCE_SETTLEMENT_FAILED,
    DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID,
)
from src.apps.data_factory.services.datasource_cost import DatasourceCostService as Cost
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService as Infrastructure
from src.apps.data_factory.services.redis_protocol import BoundedRedisBuffer
from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService as Audit


class DatasourceDiagnosticTests(SimpleTestCase):
    def test_report_keeps_formatted_reason_counts_stage_and_identifiers(self):
        with Audit.source({'case_id': 12, 'source_stage': 'parameter_posterior', 'template_id': 30,
                           'password': 'AUTO_PRIVATE', 'context': {'token': 'AUTO_PRIVATE'}}), Infrastructure.scope():
            with self.assertRaises(DataFactoryError) as caught:
                Cost.sql('x' * 100001)
            message = Infrastructure.summary()
            self.assertIn('100000', message)
            self.assertIn('100001', message)
            self.assertIn('请检查', message)
            self.assertIn('CaseID：12', message)
            self.assertIn('场景后置', message)
            self.assertNotIn('AUTO_PRIVATE', message)
            self.assertNotIn('{}', message)
            self.assertEqual(Infrastructure.current()[0].message, caught.exception.msg)

    def test_later_audit_context_enriches_instead_of_losing_the_root_reason(self):
        error = DataFactoryError(DATASOURCE_GOVERNOR_UNAVAILABLE)
        with Infrastructure.scope():
            Infrastructure.capture(error)
            Infrastructure.annotate(error, request_id='AUTO_REQUEST', database_id=7)
            Infrastructure.capture(error)
            self.assertEqual(len(Infrastructure.current()), 1)
            self.assertIn('AUTO_REQUEST', Infrastructure.summary())
            self.assertIn('数据源ID：7', Infrastructure.summary())

    def test_diagnostics_do_not_echo_unknown_values_or_repeat_ids(self):
        error = DataFactoryError(DATASOURCE_GOVERNOR_UNAVAILABLE)
        with Audit.source({'case_id': 'AUTO_PRIVATE', 'source_stage': 'AUTO_PRIVATE'}):
            Infrastructure.annotate(error, task_id=4, password='AUTO_PRIVATE')
            Infrastructure.annotate(error, task_id=4)
        self.assertNotIn('AUTO_PRIVATE', error.msg)
        self.assertEqual(error.msg.count('任务ID：4'), 1)

    def test_distinct_reasons_with_same_error_code_survive_summary(self):
        with Infrastructure.scope():
            for reason in ('Redis返回结果超过元素数上限，请缩小范围', 'ES查询请求过大，请减少条件'):
                with self.assertRaises(DataFactoryError):
                    Cost.reject(reason)
            self.assertEqual(len(Infrastructure.current()), 2)
            self.assertIn('Redis返回结果超过元素数', Infrastructure.summary())
            self.assertIn('ES查询请求过大', Infrastructure.summary())

    def test_policy_error_names_field_actual_value_and_range(self):
        with patch.object(Governor, 'policy', wraps=Governor.policy), patch(
                'src.apps.data_factory.services.datasource_governor.SystemConfigService.get',
                return_value={'mysql': {'concurrency': 1}}), Infrastructure.scope():
            with self.assertRaises(DataFactoryError) as caught:
                Governor.policy()
            self.assertIn('mysql.concurrency', caught.exception.msg)
            self.assertIn('当前值为 1', caught.exception.msg)
            self.assertIn('最小值为2', caught.exception.msg)
            self.assertIn('配置管理', caught.exception.msg)

    def test_policy_cross_field_error_is_explained_without_exposing_input(self):
        with patch('src.apps.data_factory.services.datasource_governor.SystemConfigService.get',
                   return_value={'mysql': {'cleanup_reserved': 6}}):
            with self.assertRaises(DataFactoryError) as caught:
                Governor.policy()
            self.assertIn('清理保留并发必须小于总并发', caught.exception.msg)
        with patch('src.apps.data_factory.services.datasource_governor.SystemConfigService.get',
                   return_value={'mysql': {'connections': 'AUTO_PRIVATE'}}):
            with self.assertRaises(DataFactoryError) as caught:
                Governor.policy()
            self.assertNotIn('AUTO_PRIVATE', caught.exception.msg)

    def test_invalid_transaction_count_does_not_suggest_raising_limits(self):
        with patch.object(Governor, 'target_policy', return_value=(SimpleNamespace(transaction_statement_budget=8), None, 'group')), \
                patch.object(Governor, 'transaction_capacity', return_value=8):
            with self.assertRaises(DataFactoryError) as caught:
                with Governor.transaction_budget(Mock(), 0):
                    self.fail('invalid budget executed')
        self.assertIn('当前为 0', caught.exception.msg)
        self.assertIn('不要调大配额', caught.exception.msg)

    def test_release_failure_distinguishes_unknown_result_from_release_only(self):
        with patch.object(Governor, 'change', side_effect=RuntimeError('AUTO_PRIVATE')):
            for unknown, expected in ((True, '原操作结果仍待确认'), (False, '这不等于原操作执行失败')):
                with self.subTest(unknown=unknown), self.assertRaises(DataFactoryError) as caught:
                    Governor.release(('AUTO_GROUP', 'AUTO_OWNER'), unknown=unknown)
                self.assertEqual(caught.exception.code, DATASOURCE_SETTLEMENT_FAILED.code)
                self.assertIn(expected, caught.exception.msg)
                self.assertIn('AUTO_OWNER', caught.exception.msg)
                self.assertNotIn('AUTO_PRIVATE', caught.exception.msg)
        with Governor._closed_lock:
            Governor._pending_releases.discard(('AUTO_GROUP', 'AUTO_OWNER'))

    def test_internal_cleanup_error_has_safe_reference_and_specific_category(self):
        for error, reason in ((OperationalError('AUTO_PRIVATE'), '平台控制数据库访问失败'),
                              (RuntimeError('AUTO_PRIVATE'), '平台清理内部处理异常')):
            with patch('src.common.logging.log.system.error') as logger, Infrastructure.scope():
                result = Infrastructure.internal_cleanup_error(error, 'AUTO_STAGE', execution_id=9)
                self.assertIn(reason, result.msg)
                self.assertIn('工厂执行ID：9', result.msg)
                self.assertNotIn('AUTO_PRIVATE', result.msg)
                reference = logger.call_args.args[1]
                self.assertIn(reference, result.msg)
                self.assertEqual(len(reference), 32)
                self.assertNotIn('AUTO_PRIVATE', str(logger.call_args))

    def test_redis_limits_explain_counts_or_bytes_without_partial_results(self):
        cases = [(b'*3', '3 个元素', '2 个'), (b'$1048577', '1048577 字节', '1048576')]
        for header, actual, limit in cases:
            with self.subTest(header=header), patch(
                    'src.apps.data_factory.services.redis_protocol.SystemConfigService.get_ranged_int', return_value=2):
                buffer = BoundedRedisBuffer(Mock(readline=Mock(return_value=header)))
                with self.assertRaises(DataFactoryError) as caught:
                    buffer.readline()
                self.assertIn(actual, caught.exception.msg)
                self.assertIn(limit, caught.exception.msg)
                self.assertIn('请缩小用例查询范围', caught.exception.msg)

    def test_sql_and_redis_session_denials_name_the_operation(self):
        for operation, call in [('SLEEP', lambda: Cost.sql('SELECT SLEEP(1)')),
                                ('KEYS', lambda: Cost.redis(['KEYS', '*']))]:
            with self.subTest(operation=operation), self.assertRaises(DataFactoryError) as caught:
                call()
            self.assertIn(operation, caught.exception.msg)
            self.assertIn('请修改用例', caught.exception.msg)

    def test_es_invalid_pagination_identifies_the_parameter_without_echoing_arbitrary_value(self):
        for query in ({'from': -1}, {'size': 'AUTO_PRIVATE'}):
            with self.assertRaises(DataFactoryError) as caught:
                Cost.elasticsearch('example', query)
            self.assertIn('请修改用例查询配置', caught.exception.msg)
            self.assertNotIn('AUTO_PRIVATE', caught.exception.msg)

    def test_es_snapshot_failure_still_does_not_delete_any_document(self):
        from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as Resources
        snapshot = SimpleNamespace(index='example', document_id='1001', tenant='7', connection_id=10,
                                   rule=SimpleNamespace(tenant_path='tenant_id'))
        with patch.object(Resources, 'document') as delete, self.assertRaises(DataFactoryError) as caught:
            Resources.check_owner({'_id': '1001', '_source': {'tenant_id': '8'}}, snapshot)
        self.assertEqual(caught.exception.code, DATA_FACTORY_ES_CLEANUP_OWNERSHIP_INVALID.code)
        self.assertIn('文档ID或租户字段', caught.exception.msg)
        self.assertIn('文档ID：1001', caught.exception.msg)
        delete.assert_not_called()

    def test_cleanup_validation_identifies_bad_field(self):
        from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as Resources
        with self.assertRaises(DataFactoryError) as caught:
            Resources.normalize([{'datasource_alias_id': 1, 'index_template': 'example', 'timeout_seconds': 1}])
        self.assertIn('timeout_seconds', caught.exception.msg)
        self.assertIn('最小值为', caught.exception.msg)

    def test_es_size_error_shows_requested_and_configured_limits_before_network_call(self):
        from src.apps.data_factory.services.data_source_query import DataFactoryDatasourceQuery as Query
        with patch.object(Query, 'max_rows', return_value=100), patch(
                'src.apps.data_factory.services.data_source_query.open_elasticsearch_request') as network:
            with self.assertRaises(DataFactoryError) as caught:
                Query._query_elasticsearch.__wrapped__(Query, Mock(), 'example', {'size': 101})
        self.assertIn('100 条', caught.exception.msg)
        self.assertIn('size为 101', caught.exception.msg)
        self.assertIn('未发送', caught.exception.msg)
        network.assert_not_called()

    def test_factory_case_cleanup_does_not_replace_actual_reason_with_fail_count(self):
        from src.apps.data_factory.services.case_config_runner import DataFactoryCaseConfigRunner
        runner = DataFactoryCaseConfigRunner(1, 12, 1, 0, Mock(), Mock())
        runner.auto_cleanup_execution_ids = [7]
        reason = 'ES文档仍存在，索引：example，文档ID：1001。请检查删除同步后重试'
        with patch('src.apps.data_factory.services.case_config_runner.DataFactoryCleanup.cleanup_execution',
                   return_value={'fail': 1, 'errors': [{'error': reason}]}):
            with self.assertRaises(DataFactoryError) as caught:
                runner.cleanup()
        self.assertIn(reason, caught.exception.msg)
        self.assertIn('工厂执行 7', caught.exception.msg)

    def test_es_cleanup_timeout_reports_its_own_timeout_not_the_global_one(self):
        from src.apps.data_factory.services.data_source_error import DataSourceErrorService
        with self.assertRaises(DataFactoryError) as caught:
            DataSourceErrorService.raise_elasticsearch_transport_error(SimpleNamespace(id=10), TimeoutError(), timeout=5)
        self.assertIn('5 秒', caught.exception.msg)
        self.assertIn('数据源ID：10', caught.exception.msg)
        self.assertIn('最终结果尚未确认', caught.exception.msg)

    def test_audit_distinguishes_rejected_before_send_and_incomplete_response(self):
        from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditHandle
        for not_sent in (True, False):
            target = SimpleNamespace(request_id='AUTO_REQUEST', database_id=7, source_detail={},
                                     slow_threshold_ms=20000)
            with self.subTest(not_sent=not_sent), patch.object(Audit, 'save_completion'), patch.object(Audit, 'notify_slow'):
                with self.assertRaises(DataFactoryError) as caught:
                    Cost.reject('ES查询条数超过上限，请修改用例查询配置', not_sent=not_sent)
                Audit.finish_failure(SqlExecutionAuditHandle(target, 0), caught.exception, 10)
                self.assertIn('ES查询条数超过上限', target.error_message)
                self.assertEqual(target.source_detail['outcome_unknown'], not not_sent)
                self.assertIn('AUTO_REQUEST', target.error_message)

    def test_report_persistence_keeps_the_specific_reason_and_does_not_count_business_failure(self):
        from mangotools.enums import TaskEnum
        from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
        from src.apps.test_center.services.test_suite.infrastructure import TestSuiteInfrastructureService
        detail = SimpleNamespace(id=7, retry=1, status=TaskEnum.PROCEED.value, test_suite_id=8,
                                 summary_data=None, save=Mock())
        suite = SimpleNamespace(id=8, status=TaskEnum.PROCEED.value)
        message = 'Redis返回数组声明包含 3000 个元素，超过上限 2000 个。请缩小用例查询范围（数据源ID：7，请求编号：AUTO_REQUEST）'
        issues = [DatasourceInfrastructureIssue(code=34187, message=message)]
        with patch('src.apps.test_center.services.test_suite.infrastructure.TestSuiteDetails.objects') as details, \
                patch('src.apps.test_center.services.test_suite.infrastructure.TestSuite.objects') as suites:
            details.filter.return_value.values_list.return_value.get.return_value = 8
            details.select_for_update.return_value.get.return_value = detail
            suites.select_for_update.return_value.get.return_value = suite
            accepted = TestSuiteInfrastructureService.block.__wrapped__(TestSuiteInfrastructureService, 7, 1, issues)
        self.assertTrue(accepted)
        self.assertIn(message, detail.error_message)
        self.assertEqual(detail.failure_description, message)
        self.assertEqual(detail.fail, 0)
        self.assertEqual(detail.summary_data['meta']['execution_control']['issues'][0]['message'], message)
