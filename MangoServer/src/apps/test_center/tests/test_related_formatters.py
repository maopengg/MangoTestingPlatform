from django.test import SimpleTestCase

from src.apps.test_center.formatters import related


class RelatedFormatterImportTests(SimpleTestCase):
    def test_lazy_serializer_imports_resolve(self):
        formatter_names = (
            "format_project",
            "format_project_product",
            "format_product_module",
            "format_product_module_compact",
            "format_notice_group",
            "format_test_object",
            "format_test_suite",
            "format_data_source",
        )

        for formatter_name in formatter_names:
            with self.subTest(formatter=formatter_name):
                self.assertIsNone(getattr(related, formatter_name)(None))
