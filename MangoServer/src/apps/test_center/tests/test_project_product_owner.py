from django.test import SimpleTestCase

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializers
from src.apps.test_center.api.serializers.test_object import TestObjectSerializers
from src.apps.test_center.models import TestObject


class ProjectProductOwnerTests(SimpleTestCase):
    def test_owner_is_written_on_product_and_hidden_from_test_object(self):
        owners_field = ProjectProductSerializers().fields['owners']
        self.assertTrue(owners_field.required)
        self.assertFalse(owners_field.allow_empty)
        self.assertNotIn('executor_name', TestObjectSerializers().fields)
        self.assertNotIn('executor_name', {field.name for field in TestObject._meta.fields})
