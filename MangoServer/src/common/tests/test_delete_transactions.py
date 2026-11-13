from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from django.db import connections, models, transaction
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.db.migrations.state import ModelState, StateApps
from django.db.models.deletion import ProtectedError
from django.http import QueryDict
from django.test import override_settings

from src.common.exceptions import CommonError, RESOURCE_DELETE_PROTECTED, SAVE_VALIDATION_FAILED
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_msg import RESPONSE_MSG_0005, RESPONSE_MSG_0029, RESPONSE_MSG_0210


class _DeleteTestRouter:
    def db_for_read(self, model, **hints):
        return 'delete_transaction_test' if model._meta.app_label == 'delete_tx_fixture' else None

    db_for_write = db_for_read


class DeleteTransactionTests(unittest.TestCase):
    def setUp(self):
        self.alias = 'delete_transaction_test'
        self.db = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'OPTIONS': {},
            'TIME_ZONE': None, 'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False,
            'AUTOCOMMIT': True, 'ATOMIC_REQUESTS': False,
        }, alias=self.alias)
        connections[self.alias] = self.db
        self.addCleanup(self.close)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(override_settings(DATABASE_ROUTERS=[_DeleteTestRouter()]))
        registry = StateApps([], {})

        def fixture(name, fields):
            model = ModelState('delete_tx_fixture', name,
                               [('id', models.AutoField(primary_key=True)), *fields]).render(registry)
            with self.db.schema_editor() as editor:
                editor.create_model(model)
            return model

        self.Item = fixture('Item', [('name', models.CharField(max_length=64)),
                                     ('blocked', models.BooleanField(default=False))])
        self.Audit = fixture('Audit', [('item_id', models.IntegerField())])
        self.Owned = fixture('Owned', [('kind', models.CharField(max_length=32))])
        self.Item.objects.bulk_create([self.Item(id=1, name='first'), self.Item(id=2, name='second')])
        self.delete_calls = []

        def delete(instance):
            self.delete_calls.append(instance.pk)
            if instance.blocked:
                raise ProtectedError('private relation details', {instance})
            return models.Model.delete(instance)

        self.Item.delete = delete
        self.crud = ModelCRUD()
        self.crud.model = self.Item
        self.crud.has_instance_data_scope_permission = Mock(return_value=True)
        self.crud.capture_config_snapshot = Mock(side_effect=lambda item: SimpleNamespace(snapshot={'id': item.pk}))
        self.crud.record_config_delete = Mock(side_effect=lambda item, before, **kwargs:
                                             self.Audit.objects.create(item_id=before['id']))
        self.crud.asynchronous_callback = Mock()

    def close(self):
        self.db.close()
        del connections[self.alias]

    def request(self, query='id[]=1&id[]=2'):
        return SimpleNamespace(query_params=QueryDict(query), user={'id': 7})

    def test_batch_success_commits_deletions_and_audit_together(self):
        response = self.crud.delete(self.request())
        self.assertEqual(response.data['code'], RESPONSE_MSG_0005[0])
        self.assertEqual(self.Item.objects.count(), 0)
        self.assertEqual(self.Audit.objects.count(), 2)

    def test_second_protected_target_rolls_back_first_and_its_audit(self):
        self.Item.objects.filter(pk=2).update(blocked=True)
        with patch('src.common.decorators.error_response.report_system_error') as record:
            response = self.crud.delete(self.request())
        self.assertEqual(response.data['code'], RESOURCE_DELETE_PROTECTED.code)
        self.assertNotIn('private', response.data['msg'])
        self.assertEqual(self.delete_calls, [1, 2])
        self.assertEqual(self.Item.objects.count(), 2)
        self.assertEqual(self.Audit.objects.count(), 0)
        record.assert_not_called()

    def test_later_permission_denial_is_checked_before_any_deletion(self):
        self.crud.has_instance_data_scope_permission.side_effect = lambda request, item: item.pk == 1
        response = self.crud.delete(self.request())
        self.assertEqual(response.data['code'], RESPONSE_MSG_0210[0])
        self.assertEqual(self.Item.objects.count(), 2)
        self.assertEqual(self.delete_calls, [])
        self.crud.capture_config_snapshot.assert_not_called()

    def test_missing_later_target_does_not_delete_earlier_target(self):
        response = self.crud.delete(self.request('id[]=1&id[]=999'))
        self.assertEqual(response.data['code'], RESPONSE_MSG_0029[0])
        self.assertEqual(self.Item.objects.count(), 2)
        self.assertEqual(self.delete_calls, [])

    def test_audit_failure_rolls_back_single_and_batch_deletion(self):
        self.crud.record_config_delete.side_effect = CommonError(SAVE_VALIDATION_FAILED, value=('example',))
        for query in ('id=1', 'id[]=1&id[]=2'):
            response = self.crud.delete(self.request(query))
            self.assertEqual(response.data['code'], SAVE_VALIDATION_FAILED.code)
            self.assertEqual(self.Item.objects.count(), 2)
        self.crud.asynchronous_callback.assert_not_called()

    def test_refresh_callback_runs_only_after_outer_transaction_commits(self):
        with transaction.atomic(using=self.alias):
            response = self.crud.delete(self.request('id=1&parent_id=8'))
            self.assertEqual(response.data['code'], RESPONSE_MSG_0005[0])
            self.crud.asynchronous_callback.assert_not_called()
        self.crud.asynchronous_callback.assert_called_once_with('8')

    def test_rollback_discards_refresh_callback(self):
        with transaction.atomic(using=self.alias):
            self.crud.delete(self.request('id=1'))
            transaction.set_rollback(True, using=self.alias)
        self.assertEqual(self.Item.objects.count(), 2)
        self.crud.asynchronous_callback.assert_not_called()

    def test_duplicate_ids_are_deleted_once(self):
        self.crud.delete(self.request('id[]=1&id[]=1'))
        self.assertEqual(self.delete_calls, [1])
        self.assertEqual(self.Audit.objects.count(), 1)

    def test_internal_delete_is_atomic_with_audit(self):
        class InternalCRUD(ModelCRUD):
            pass
        InternalCRUD.model = self.Item
        with patch.object(InternalCRUD, 'capture_config_snapshot', return_value=SimpleNamespace(snapshot={})), \
                patch.object(InternalCRUD, 'record_config_delete',
                             side_effect=CommonError(SAVE_VALIDATION_FAILED, value=('example',))):
            with self.assertRaises(CommonError):
                InternalCRUD.inside_delete(1)
        self.assertEqual(self.Item.objects.count(), 2)

    def test_product_cleanup_is_rolled_back_when_final_parent_delete_is_protected(self):
        from src.apps.auto_api.models import ApiCase, ApiHeaders, ApiInfo, ApiPublic
        from src.apps.auto_pytest.models import PytestProduct
        from src.apps.auto_ui.models import Page, PageSteps, UiCase, UiPublic
        from src.apps.task_center.models import Tasks
        from src.apps.test_center.models import FileData, ProductModule, ProjectProduct, TestObject, TestSuite, TestSuiteDetails
        for kind in ('detail', 'suite', 'file'):
            self.Owned.objects.create(kind=kind)
        with ExitStack() as stack:
            for model in (ProductModule, TestObject, ApiInfo, ApiCase, ApiPublic, ApiHeaders,
                          Page, PageSteps, UiCase, UiPublic, Tasks, PytestProduct):
                stack.enter_context(patch.object(model.objects, 'filter')).return_value.exists.return_value = False
            for model, kind in ((TestSuiteDetails, 'detail'), (TestSuite, 'suite'), (FileData, 'file')):
                stack.enter_context(patch.object(model.objects, 'filter', return_value=self.Owned.objects.filter(kind=kind)))
            stack.enter_context(patch('src.apps.test_center.models.catalog.transaction.get_connection', return_value=self.db))
            stack.enter_context(patch.object(models.Model, 'delete', side_effect=ProtectedError('protected', [])))
            with self.assertRaises(ProtectedError):
                ProjectProduct(id=9, project_id=1, name='示例产品').delete()
        self.assertEqual(self.Owned.objects.count(), 3)

    def test_file_objects_are_not_removed_before_database_commit_or_after_rollback(self):
        from src.apps.test_center.models import FileData
        for rollback in (True, False):
            storage = Mock()
            item = FileData(id=1, name='example', type=0, test_file='test_file/example.txt')
            item.test_file.storage = storage
            with patch.object(models.Model, 'delete', return_value=(1, {})):
                with transaction.atomic(using=self.alias):
                    item.delete(using=self.alias)
                    storage.delete.assert_not_called()
                    if rollback:
                        transaction.set_rollback(True, using=self.alias)
            if rollback:
                storage.delete.assert_not_called()
            else:
                storage.delete.assert_called_once_with('test_file/example.txt')
