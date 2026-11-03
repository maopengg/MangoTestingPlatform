import ast
from importlib import import_module
from pathlib import Path

from django.conf import settings
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext

from src.apps.auto_api.api.serializers.api_headers import ApiHeadersSerializersC
from src.apps.auto_api.models import ApiHeaders
from src.apps.test_center.models import Project, ProjectProduct
from src.apps.user.models import User


class ProductDisplayQueriesTests(SimpleTestCase):
    def test_all_explicit_product_formatters_preload_the_complete_display_graph(self):
        checked = 0
        compiler_connection = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}, alias='display_sql')
        for path in (Path(settings.BASE_DIR) / 'src' / 'apps').rglob('*.py'):
            if '/api/serializers/' not in str(path):
                continue
            for node in ast.parse(path.read_text()).body:
                if not isinstance(node, ast.ClassDef):
                    continue
                declarations = [item for item in node.body if isinstance(item, ast.Assign)
                                and 'formatter=format_project_product,' in ast.unparse(item.value)]
                if not declarations:
                    continue
                module = '.'.join(path.relative_to(settings.BASE_DIR).with_suffix('').parts)
                serializer = getattr(import_module(module), node.name)
                with self.subTest(serializer=module + '.' + node.name):
                    query = serializer.setup_eager_loading(serializer.Meta.model.objects.all())
                    sql, _params = query.query.get_compiler(connection=compiler_connection).as_sql()
                    self.assertIn('project_product__owners', query._prefetch_related_lookups)
                    self.assertIn('project', query.query.select_related['project_product'])
                    self.assertIn('update_user', query.query.select_related['project_product']['project'])
                    self.assertIn('update_user', query.query.select_related['project_product'])
                    self.assertTrue(serializer().fields['project_product'].cache_representation)
                    self.assertTrue(sql)
                    checked += 1
        self.assertGreaterEqual(checked, 28)

    def test_real_orm_uses_two_queries_and_keeps_the_legacy_response(self):
        # 独立内存连接，仅建本测试所需的临时表；不访问环境库、不执行迁移。
        alias = 'product_display_performance'
        database = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'OPTIONS': {}, 'TIME_ZONE': None, 'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'ATOMIC_REQUESTS': False,
        }, alias=alias)
        database.ensure_connection()
        connections[alias] = database
        try:
            with database.cursor() as cursor:
                for model in (User, Project, ProjectProduct, ProjectProduct.owners.through, ApiHeaders):
                    columns = ', '.join(f'"{field.column}" {field.db_type(database)}'
                                        + (' PRIMARY KEY' if field.primary_key else '')
                                        for field in model._meta.concrete_fields)
                    cursor.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
            user = User(id=1, name='示例用户', username='reader@example.com', config={
                'personal_cache': {'preferences': {'title': '偏好设置', 'items': {'selected_environment': {'value': 1}}}},
            })
            User.objects.using(alias).bulk_create([user])
            project = Project(id=1, name='示例项目', update_user_id=1)
            Project.objects.using(alias).bulk_create([project])
            product = ProjectProduct(id=1, name='示例产品', project_id=1, update_user_id=1)
            ProjectProduct.objects.using(alias).bulk_create([product])
            through = ProjectProduct.owners.through
            through.objects.using(alias).bulk_create([through(projectproduct_id=1, user_id=1)])
            ApiHeaders.objects.using(alias).bulk_create([
                ApiHeaders(id=index, key=f'X-Example-{index}', value='example', project_product_id=1, update_user_id=1)
                for index in range(1, 21)
            ])

            class LegacySerializer(ApiHeadersSerializersC):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.fields['project_product'].cache_representation = False

            legacy = ApiHeaders.objects.using(alias).select_related(
                'project_product', 'project_product__project', 'update_user',
            )
            with CaptureQueriesContext(database) as before:
                expected = LegacySerializer(legacy, many=True).data
            optimized = ApiHeadersSerializersC.setup_eager_loading(ApiHeaders.objects.using(alias).all())
            with CaptureQueriesContext(database) as after:
                actual = ApiHeadersSerializersC(optimized, many=True).data
            self.assertEqual(actual, expected)
            self.assertEqual(len(before), 61)
            self.assertEqual(len(after), 2)
        finally:
            del connections[alias]
            database.connection.close()
