from django.test import SimpleTestCase

from src.apps.test_center.models import TestSuiteDetails


class TestSuiteDetailIndexTests(SimpleTestCase):
    def test_case_history_count_has_covering_index(self):
        indexes = {index.name: index for index in TestSuiteDetails._meta.indexes}

        self.assertIn('idx_detail_case_type', indexes)
        self.assertEqual(indexes['idx_detail_case_type'].fields, ['case_id', 'type'])
        self.assertIsNone(indexes['idx_detail_case_type'].condition)
