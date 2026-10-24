from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.data_factory.models import Database
from src.apps.test_center.api.serializers.data_source import DataSourceSerializer
from src.apps.test_center.exceptions import TestCenterError, DATA_SOURCE_CONNECTION_DUPLICATED
from src.apps.test_center.services.data_source_configuration import DataSourceConfigurationService


class DataSourceConfigurationTests(SimpleTestCase):
    def connection(self, **overrides):
        return Database(**{
            'id': 1, 'db_type': 0, 'source_category': 0,
            'host': 'mysql.example.com', 'port': 3306, 'user': 'reader',
            'password': 'old-secret', 'display_name': '已有连接',
            'file_path': '', 'extra_config': {}, **overrides,
        })

    def queryset(self, rows):
        result = MagicMock()
        result.filter.side_effect = lambda **values: self.queryset([
            row for row in rows if all(getattr(row, key) == value for key, value in values.items())
        ])
        result.exclude.side_effect = lambda **values: self.queryset([
            row for row in rows if not all(getattr(row, key) == value for key, value in values.items())
        ])
        result.only.return_value = result
        result.order_by.return_value = result
        result.__iter__.side_effect = lambda: iter(rows)
        return result

    def setUp(self):
        super().setUp()
        self.rows = [self.connection()]
        query = patch.object(Database.objects, 'filter', side_effect=lambda **values: self.queryset([
            row for row in self.rows if all(getattr(row, key) == value for key, value in values.items())
        ]))
        query.start()
        self.addCleanup(query.stop)

    def payload(self, **overrides):
        return {
            'db_type': 0, 'source_category': 0, 'display_name': '新名称',
            'host': 'mysql.example.com', 'port': 3306, 'user': 'reader',
            'password': 'new-secret', 'extra_config': {}, **overrides,
        }

    def test_create_rejects_same_identity_regardless_of_name_password(self):
        with self.assertRaises(TestCenterError) as raised:
            DataSourceSerializer(data=self.payload()).is_valid(raise_exception=True)
        self.assertEqual(raised.exception.code, DATA_SOURCE_CONNECTION_DUPLICATED.code)
        self.assertNotIn('old-secret', raised.exception.msg)
        self.assertNotIn('new-secret', raised.exception.msg)

    def test_host_whitespace_and_case_do_not_bypass_check(self):
        with self.assertRaises(TestCenterError):
            DataSourceSerializer(data=self.payload(host='  MYSQL.EXAMPLE.COM  ')).is_valid(raise_exception=True)

    def test_different_account_port_or_type_is_allowed(self):
        for values in [{'user': 'writer'}, {'user': 'Reader'}, {'port': 3307}, {'db_type': 1}]:
            with self.subTest(values=values):
                DataSourceConfigurationService.validate_unique(self.payload(**values))

    def test_new_host_is_normalized_on_save(self):
        serializer = DataSourceSerializer(data=self.payload(host='  OTHER.EXAMPLE.COM  '))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['host'], 'other.example.com')

    def test_partial_update_excludes_self_and_preserves_password(self):
        serializer = DataSourceSerializer(instance=self.rows[0], data={'display_name': '重命名', 'password': ''},
                                          partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('password', serializer.validated_data)

    def test_editing_connection_into_another_identity_is_rejected(self):
        self.rows.append(self.connection(id=2, user='writer'))
        with self.assertRaises(TestCenterError):
            DataSourceSerializer(instance=self.rows[1], data={'user': 'reader'}, partial=True).is_valid(
                raise_exception=True)

    def test_existing_host_is_normalized_during_comparison(self):
        self.rows = [self.connection(host=' MYSQL.EXAMPLE.COM ')]
        with self.assertRaises(TestCenterError):
            DataSourceConfigurationService.validate_unique(self.payload())

    def test_sqlite_identity_only_uses_normalized_file_path(self):
        self.rows = [self.connection(db_type=2, file_path='/tmp/mango/example/../database.sqlite')]
        with self.assertRaises(TestCenterError):
            DataSourceConfigurationService.validate_unique(
                self.payload(db_type=2, file_path='/tmp/mango/database.sqlite', user='another'))
        attrs = self.payload(db_type=2, file_path='/tmp/mango/other/../other.sqlite')
        DataSourceConfigurationService.validate_unique(attrs)
        self.assertEqual(attrs['file_path'], str(Path('/tmp/mango/other.sqlite').resolve()))

    def test_es_defaults_and_equivalent_prefixes_are_duplicates(self):
        self.rows = [self.connection(db_type=20, extra_config={'path_prefix': '/gateway/'})]
        with self.assertRaises(TestCenterError):
            DataSourceConfigurationService.validate_unique(self.payload(db_type=20, extra_config={'scheme': 'http',
                                                                                                  'path_prefix': 'gateway',
                                                                                                  'verify_certs': False}))

    def test_es_protocol_and_prefix_distinguish_connections(self):
        self.rows = [self.connection(db_type=20, extra_config={})]
        for extra in [{'scheme': 'https'}, {'path_prefix': '/gateway'}]:
            DataSourceConfigurationService.validate_unique(self.payload(db_type=20, extra_config=extra))

    def test_redis_password_and_ssl_do_not_create_a_new_identity(self):
        self.rows = [self.connection(db_type=10)]
        with self.assertRaises(TestCenterError):
            DataSourceConfigurationService.validate_unique(self.payload(db_type=10, extra_config={'ssl': True}))
