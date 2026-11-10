"""仅由隔离SQLite内存测试入口运行，不连接业务库或执行迁移。"""
import unittest
import re
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection
from django.utils import timezone
from sqlalchemy import create_engine, event, text

from src.apps.auto_api.enums.resource_cleanup import ApiResourceCleanupStatus as State
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseExecutionTrace, ApiCaseExecutionResource
from src.apps.auto_api.schemas.resource_cleanup import ApiResourceProof
from src.apps.auto_api.services.resource_cleanup import ApiResourceExecutionManager as Manager, ApiResourceCleanupService as Service
from src.apps.auto_api.services.resource_cleanup_io import ApiResourceCleanupIO as IO
from src.apps.auto_api.tests.test_resource_cleanup import rule_data, proof_data, document
from src.apps.data_factory.services.cleanup_resource import DataFactoryCleanupResourceService as ES


class ResourceLedgerDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor != 'sqlite' or connection.settings_dict['NAME'] != ':memory:':
            raise unittest.SkipTest('此测试只允许显式隔离的SQLite内存库')
        connection.disable_constraint_checking()
        with connection.schema_editor() as editor:
            for model in (ApiCase, ApiCaseExecutionTrace, ApiCaseExecutionResource):
                editor.create_model(model)
        connection.disable_constraint_checking()

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            for model in (ApiCaseExecutionResource, ApiCaseExecutionTrace, ApiCase):
                editor.delete_model(model)
        super().tearDownClass()

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.case = ApiCase.objects.create(project_product_id=3, module_id=4, case_people_id=5, name='AUTO_fixture')
        self.trace = ApiCaseExecutionTrace.objects.create(case_id=self.case.id, trace_id=f'AUTO_trace_{self.case.id}',
            source_type=4, started_at=timezone.now(), finished_at=timezone.now())
        self.rule = rule_data()
        self.rule['children'] = self.rule['children'][:1]
        self.case.resource_cleanup = [self.rule]
        self.case.save(update_fields=['resource_cleanup'])
        self.clock = 0
        self.documents = {}
        self.deleted = []
        self.interrupt = False
        self.engine = create_engine('sqlite:///:memory:')
        @event.listens_for(self.engine, 'before_cursor_execute', retval=True)
        def sqlite_fixture_sql(connection, cursor, statement, parameters, context, executemany):
            # SQLite无这两个MySQL语法，仅在隔离夹具适配，生产语句与提交事件保持原样。
            statement = statement.removesuffix(' FOR UPDATE')
            if statement.startswith('DELETE '):
                statement = re.sub(r' LIMIT [0-9]+$', '', statement)
            return statement, parameters
        self.addCleanup(self.engine.dispose)
        with self.engine.begin() as sql:
            sql.exec_driver_sql('CREATE TABLE project (_id INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT, group_id TEXT, '
                               'version TEXT, tenant_id TEXT, create_employee_id TEXT, name TEXT)')
            sql.exec_driver_sql('CREATE TABLE project_member (project_id TEXT, tenant_id TEXT)')
            sql.exec_driver_sql("INSERT INTO project VALUES (999,'other','other_doc','2','123','456','existing')")
            sql.exec_driver_sql("INSERT INTO project_member VALUES ('other','123')")
        targets = proof_data()
        self.stack.enter_context(patch.object(IO, 'binding', side_effect=lambda alias, *a, **k:
            (SimpleNamespace(), targets.sql_target if k.get('sql') else targets.es_target)))
        self.stack.enter_context(patch('src.apps.data_factory.services.datasource.DataFactoryDatasource.create_engine',
                                       return_value=self.engine))
        self.stack.enter_context(patch.object(ES, 'resolve_index', return_value=('project_123', 'uuid')))
        self.stack.enter_context(patch.object(ES, 'document', side_effect=self.es_document))
        self.stack.enter_context(patch('src.apps.auto_api.services.resource_cleanup.acquire_mysql_lock', return_value=True))
        self.stack.enter_context(patch('src.apps.auto_api.services.resource_cleanup.release_mysql_lock', return_value=True))
        self.stack.enter_context(patch('src.apps.auto_api.services.resource_cleanup.monotonic', side_effect=lambda: self.clock))
        self.stack.enter_context(patch('src.apps.task_center.services.execution.cooperative_executor.cooperative_sleep',
                                      side_effect=self.pause))
        self.stack.enter_context(patch('src.apps.data_factory.services.infrastructure.DatasourceInfrastructureService.resolve_verified_requests'))
        self.cache = {'tenant': '123', 'employee': '456'}
        setup = SimpleNamespace(test_data=SimpleNamespace(set_cache=self.cache.__setitem__, get_cache=self.cache.__getitem__))
        self.manager = Manager(self.case, self.trace, setup, [self.rule])
        self.manager.activate(10, 30)

    def pause(self, seconds):
        self.clock += seconds

    def es_document(self, target, index, doc_id, **kwargs):
        value = self.documents.get(doc_id)
        if kwargs.get('delete'):
            self.deleted.append(doc_id)
            self.documents.pop(doc_id, None)
            if self.interrupt:
                self.interrupt = False
                raise KeyboardInterrupt()
            return {'result': 'deleted'}
        return value

    def create(self, *, respond=True):
        name = self.cache['api_resource_project']
        record = self.manager.before_request(SimpleNamespace(method='POST', protocol_type='http',
            request_body={'name': name}), 20, 0)
        with self.engine.begin() as sql:
            sql.execute(text('INSERT INTO project(id,group_id,version,tenant_id,create_employee_id,name) '
                             "VALUES ('9001','8001','2','123','456',:name)"), {'name': name})
            sql.exec_driver_sql("INSERT INTO project_member VALUES ('9001','123')")
        # API返回前ES已同步：这是允许的API所有权情形，不是工厂存量基线。
        self.documents['8001'] = document()
        if respond:
            self.manager.after_response(record, SimpleNamespace(json={
                'data': {'projectId': '9001', 'groupId': '8001', 'projectVersion': '2'}}))
        return record

    def assert_zero_and_other_untouched(self):
        with self.engine.connect() as sql:
            self.assertEqual(sql.exec_driver_sql("SELECT id FROM project").scalars().all(), ['other'])
            self.assertEqual(sql.exec_driver_sql("SELECT project_id FROM project_member").scalars().all(), ['other'])
        self.assertNotIn('8001', self.documents)

    def test_real_ledger_and_sql_lifecycle(self):
        record = self.create()
        record.refresh_from_db()
        proof = ApiResourceProof.model_validate(record.proof)
        self.assertNotEqual(proof.root['_id'], proof.root['id'])
        self.assertNotEqual(proof.root['id'], proof.root['group_id'])
        self.manager.cleanup()
        record.refresh_from_db()
        self.assertEqual(record.status, State.CLEANED.value)
        self.assertTrue(record.proof['es_verified'])
        self.assertGreaterEqual(self.clock, 16)
        self.assert_zero_and_other_untouched()

    def test_timeout_without_response_discovers_only_original_unique_key(self):
        record = self.create(respond=False)
        self.manager.cleanup()
        record.refresh_from_db()
        self.assertEqual(record.proof['response_identity'], {})
        self.assertEqual(record.proof['root']['group_id'], '8001')
        self.assert_zero_and_other_untouched()

    def test_sql_transaction_rollback_preserves_rows_on_limit_failure(self):
        record = self.create()
        record.rule['children'][0]['max_rows'] = 1
        record.save(update_fields=['rule'])
        with self.engine.begin() as sql:
            sql.exec_driver_sql("INSERT INTO project_member VALUES ('9001','123')")
        with self.assertRaises(AutoApiError):
            self.manager.cleanup()
        record.refresh_from_db()
        self.assertEqual(record.status, State.FAILED.value)
        self.assertFalse(record.proof['sql_cleaned'])
        self.assertEqual(self.deleted, [])
        with self.engine.connect() as sql:
            self.assertEqual(sql.exec_driver_sql("SELECT count(*) FROM project_member WHERE project_id='9001'").scalar(), 2)

    def test_es_owner_mismatch_prevents_sql_and_es_deletion(self):
        record = self.create()
        self.documents['8001']['_source']['tenantId'] = 'unrelated'
        with self.assertRaises(AutoApiError):
            self.manager.cleanup()
        record.refresh_from_db()
        self.assertFalse(record.proof['sql_cleaned'])
        self.assertEqual(self.deleted, [])

    def test_process_interrupt_resumes_original_resource_no_business_replay(self):
        record = self.create()
        self.interrupt = True
        with self.assertRaises(KeyboardInterrupt):
            self.manager.cleanup()
        recovered = ApiCaseExecutionResource.objects.select_related('case', 'trace').get(id=record.id)
        self.assertTrue(recovered.proof['sql_cleaned'])
        Service.cleanup(recovered)
        recovered.refresh_from_db()
        self.assertEqual(recovered.status, State.CLEANED.value)
        self.assertEqual(self.deleted, ['8001'])
        self.assert_zero_and_other_untouched()

    def test_repeated_cleanup_is_idempotent(self):
        record = self.create()
        self.manager.cleanup()
        self.manager.cleanup()
        self.assertEqual(self.deleted, ['8001'])
        self.assertEqual(ApiCaseExecutionResource.objects.filter(trace=self.trace).count(), 1)

    def test_token_fencing_prevents_old_owner_overwrite(self):
        record = self.create()
        record.cleanup_token = 'a' * 32
        ApiCaseExecutionResource.objects.filter(id=record.id).update(cleanup_token='b' * 32)
        with self.assertRaises(AutoApiError):
            Service.persist(record, ApiResourceProof.model_validate(record.proof), status=State.CLEANED.value)
        record.refresh_from_db()
        self.assertNotEqual(record.status, State.CLEANED.value)

    def test_commit_guard_rolls_back_when_owner_changes(self):
        record = self.create()
        original = Service.check
        count = [0]
        def check(current):
            count[0] += 1
            if count[0] == 5:
                ApiCaseExecutionResource.objects.filter(id=current.id).update(cleanup_token='f' * 32)
            original(current)
        with patch.object(Service, 'check', side_effect=check), self.assertRaises(AutoApiError):
            self.manager.cleanup()
        self.assertEqual(count[0], 5)
        with self.engine.connect() as sql:
            self.assertEqual(sql.exec_driver_sql("SELECT count(*) FROM project WHERE id='9001'").scalar(), 1)
            self.assertEqual(sql.exec_driver_sql("SELECT count(*) FROM project_member WHERE project_id='9001'").scalar(), 1)
        self.assertEqual(self.deleted, [])
