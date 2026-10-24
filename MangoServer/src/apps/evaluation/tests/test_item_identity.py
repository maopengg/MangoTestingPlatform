from django.test import SimpleTestCase
from pydantic import ValidationError

from src.apps.evaluation.api.serializers.dataset_item import DatasetItemSerializer
from src.apps.evaluation.api.serializers.item_result import ItemResultListSerializer
from src.apps.evaluation.models import EvaluationDatasetItem, EvaluationItemResult
from src.apps.evaluation.schemas.item import EvaluationDatasetItemPayload


class EvaluationItemIdentityTests(SimpleTestCase):
    def test_creation_uses_generated_primary_key_without_a_business_code(self):
        serializer = DatasetItemSerializer(data={"id": 999, "input_data": {"question": "现在住哪里？"}})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn("id", serializer.validated_data)
        self.assertNotIn("item_key", serializer.fields)
        self.assertNotIn("item_key", {field.name for field in EvaluationDatasetItem._meta.fields})

    def test_payload_does_not_require_identity_or_allow_client_supplied_primary_keys(self):
        self.assertEqual(EvaluationDatasetItemPayload(input_data="question").input_data, "question")
        with self.assertRaises(ValidationError):
            EvaluationDatasetItemPayload(id=999, input_data="question")

    def test_result_primary_key_and_dataset_item_primary_key_are_distinct(self):
        row = EvaluationItemResult(id=501, execution_id=10, dataset_item_id=101)
        data = ItemResultListSerializer(row).data
        self.assertEqual(data["id"], 501)
        self.assertEqual(data["dataset_item_id"], 101)
        self.assertNotIn("item_key", data)
