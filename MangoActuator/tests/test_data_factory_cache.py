from unittest import TestCase

from src.customization.test_data import ObtainTestData


class DataFactoryCacheTests(TestCase):
    def test_data_factory_cache_participates_in_variable_replacement(self):
        test_data = ObtainTestData()
        test_data.set_data_factory_cache("智能审查任务.task_id", 1234577813)

        self.assertEqual(test_data.replace("${{智能审查任务.task_id}}"), 1234577813)
        self.assertEqual(test_data.replace("${{df.智能审查任务.task_id}}"), 1234577813)
