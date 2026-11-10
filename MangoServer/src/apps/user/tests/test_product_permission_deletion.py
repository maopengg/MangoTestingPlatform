from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import models
from django.db.models.deletion import Collector, ProtectedError
from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiCase, ApiInfo
from src.apps.auto_ui.models import Page, UiCase
from src.apps.task_center.models import Tasks
from src.apps.test_center.models import ProductModule, ProjectProduct, TestObject
from src.apps.user.models import Department, DepartmentProjectProductPermission, User


class ProductPermissionDeletionTests(SimpleTestCase):
    def test_department_and_product_own_their_permission_links(self):
        for name in ('department', 'project_product'):
            with self.subTest(field=name):
                field = DepartmentProjectProductPermission._meta.get_field(name)
                self.assertIs(field.remote_field.on_delete, models.CASCADE)

    def test_business_asset_product_relations_still_use_protect(self):
        for model in (ProductModule, TestObject, ApiCase, ApiInfo, Page, UiCase, Tasks):
            with self.subTest(model=model.__name__):
                self.assertIs(model._meta.get_field('project_product').remote_field.on_delete, models.PROTECT)

    def collection(self, *, blocked=False):
        product = ProjectProduct(id=19, project_id=1, name='待删除产品')
        links = [DepartmentProjectProductPermission(id=index, department_id=index, project_product=product)
                 for index in (1, 2)]
        other = DepartmentProjectProductPermission(id=3, department_id=1, project_product_id=20)
        module = ProductModule(id=1, project_product=product, name='受保护模块')
        queried = []

        class RelatedRows(list):
            def __init__(self, model, rows):
                super().__init__(rows)
                self.model = model
                self.query = SimpleNamespace(select_related=True)
                self.delete = MagicMock()
                self._raw_delete = MagicMock()

        def related_objects(model, fields, batch):
            rows = []
            if model is DepartmentProjectProductPermission:
                ids = {item.pk for item in batch}
                rows = [link for link in [*links, other] if link.project_product_id in ids]
            elif model is ProductModule and blocked:
                rows = [module]
            queryset = RelatedRows(model, rows)
            queried.append(queryset)
            return queryset

        collector = Collector(using='default')
        with (
            patch.object(collector, 'can_fast_delete', return_value=False),
            patch.object(collector, 'get_del_batches', side_effect=lambda objs, fields: [objs]),
            patch.object(collector, 'related_objects', side_effect=related_objects),
        ):
            if blocked:
                with self.assertRaises(ProtectedError) as error:
                    collector.collect([product])
                self.assertIn(module, error.exception.protected_objects)
            else:
                collector.collect([product])
        return collector, links, other, queried

    def test_product_delete_collects_only_its_permissions_not_departments_or_users(self):
        collector, links, other, _ = self.collection()
        self.assertEqual(collector.data[DepartmentProjectProductPermission], set(links))
        self.assertNotIn(other, collector.data[DepartmentProjectProductPermission])
        self.assertNotIn(Department, collector.data)
        self.assertNotIn(User, collector.data)

    def test_protected_business_asset_stops_collection_before_any_authorization_delete(self):
        _, links, other, queried = self.collection(blocked=True)
        for queryset in queried:
            queryset.delete.assert_not_called()
            queryset._raw_delete.assert_not_called()
        self.assertEqual([link.pk for link in links], [1, 2])
        self.assertEqual(other.pk, 3)
