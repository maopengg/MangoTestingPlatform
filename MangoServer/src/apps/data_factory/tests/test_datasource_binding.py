from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.data_factory.api.views.datasource_binding import DataFactoryDatasourceBindingCRUD
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
from src.apps.test_center.models import TestObject


class DataFactoryDatasourceBindingCRUDTests(SimpleTestCase):
    @patch.object(DataFactoryDatasourceBindingCRUD, 'get_existing_binding')
    def test_post_rejects_duplicate_alias_environment_binding(self, get_existing_binding):
        get_existing_binding.return_value = SimpleNamespace(id=7)
        request = SimpleNamespace(
            data={'datasource_alias': 1, 'environment': 0, 'data_source': 9},
            user={'id': 1},
        )

        response = DataFactoryDatasourceBindingCRUD().post(request)

        self.assertEqual(response.data['code'], 300)
        self.assertEqual(
            response.data['msg'],
            '当前逻辑数据库已绑定测试环境，请编辑现有绑定或先解绑',
        )

    @patch.object(DataFactoryDatasourceBindingCRUD, 'get_existing_binding')
    def test_internal_create_rejects_duplicate_instead_of_updating(self, get_existing_binding):
        get_existing_binding.return_value = SimpleNamespace(id=7)

        with self.assertRaises(DataFactoryError) as error:
            DataFactoryDatasourceBindingCRUD.inside_post({
                'datasource_alias': 1,
                'environment': 3,
                'data_source': 9,
            })

        self.assertIn('已绑定开发环境', error.exception.msg)

    def test_environment_name_has_readable_fallback(self):
        self.assertEqual(DataFactoryDatasourceBindingCRUD.environment_name(99), '环境99')
        self.assertEqual(DataFactoryDatasourceBindingCRUD.environment_name(None), '当前测试环境')


class DataFactoryDatasourceRuntimeStatusTests(SimpleTestCase):

    @patch('src.apps.data_factory.services.datasource.datasource.TestObject.objects.get')
    def test_entity_binding_reports_missing_test_object_as_business_error(self, get_test_object):
        get_test_object.side_effect = TestObject.DoesNotExist
        entity = SimpleNamespace(datasource_alias_id=9, name='订单')

        with self.assertRaisesMessage(
                DataFactoryError,
                '测试对象不存在或已删除，请使用存在的测试对象id查询',
        ) as raised:
            DataFactoryDatasourceResolver.resolve_entity_binding(entity, 6104)

        self.assertEqual(raised.exception.error_code, 'TEST_OBJECT_NOT_FOUND')
        self.assertEqual(raised.exception.details, {'test_object_id': 6104})

    @staticmethod
    def binding(alias_status):
        return SimpleNamespace(
            datasource_alias=SimpleNamespace(status=alias_status),
            db_c_status=1,
            db_rud_status=1,
            environment=1,
            test_object_id=None,
        )

    def test_disabled_alias_is_rejected_at_runtime(self):
        with self.assertRaisesMessage(DataFactoryError, '当前逻辑数据源已停用，请启用后再执行'):
            DataFactoryDatasourceResolver.require_alias_enabled(self.binding(0))

    @patch('src.apps.data_factory.services.datasource.datasource.SqlPermissionGuard.check')
    def test_enabled_alias_continues_to_permission_check(self, permission_check):
        binding = self.binding(1)

        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)

        permission_check.assert_called_once_with(
            'SELECT 1',
            allow_query=True,
            allow_write=True,
        )

    @patch.object(DataFactoryDatasourceResolver, 'require_alias_enabled')
    @patch('src.apps.data_factory.services.datasource.datasource.DataFactoryDatasourceBinding.objects.select_related')
    def test_binding_resolution_checks_alias_status(self, select_related, require_alias_enabled):
        binding = SimpleNamespace(
            database=SimpleNamespace(source_category=1, db_type=0),
            datasource_alias=SimpleNamespace(source_category=1, db_type=0),
        )
        queryset = select_related.return_value.filter.return_value
        queryset.order_by.return_value.first.return_value = binding

        result = DataFactoryDatasourceResolver.resolve_binding_by_env(9, 22, 1)

        self.assertIs(result, binding)
        require_alias_enabled.assert_called_once_with(binding)

    def test_sql_public_alias_accepts_enabled_relational_datasource(self):
        alias = SimpleNamespace(
            project_product_id=22,
            status=1,
            db_type=0,
        )

        DataFactoryDatasourceResolver.require_sql_public_alias(alias, 22)

    def test_sql_public_alias_rejects_redis(self):
        alias = SimpleNamespace(
            project_product_id=22,
            status=1,
            db_type=10,
        )

        with self.assertRaisesMessage(DataFactoryError, '仅支持MySQL、PostgreSQL和SQLite'):
            DataFactoryDatasourceResolver.require_sql_public_alias(alias, 22)

    def test_sql_public_alias_rejects_other_product(self):
        alias = SimpleNamespace(
            project_product_id=23,
            status=1,
            db_type=0,
        )

        with self.assertRaisesMessage(DataFactoryError, '不属于当前项目产品'):
            DataFactoryDatasourceResolver.require_sql_public_alias(alias, 22)
