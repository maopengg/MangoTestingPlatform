import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.test_center.services.reporting.test_suite.api_report_export import ApiReportExportService


class ReportExportCleanupTests(SimpleTestCase):
    def test_only_old_generated_exports_are_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path(directory, 'API测试报告_1_20260701000000.xlsx')
            recent = Path(directory, 'API测试报告_2_20261001000000.xlsx')
            manual = Path(directory, 'customer.xlsx')
            for path in [old, recent, manual]:
                path.touch()
            stamp = (datetime.now() - timedelta(days=100)).timestamp()
            os.utime(old, (stamp, stamp))
            os.utime(manual, (stamp, stamp))
            with patch('src.apps.test_center.services.reporting.test_suite.api_report_export.EXPORT_DIR', directory):
                result = ApiReportExportService.cleanup_expired_files(60)
            self.assertFalse(old.exists())
            self.assertTrue(recent.exists())
            self.assertTrue(manual.exists())
            self.assertEqual(result['report_export_deleted_file_count'], 1)
