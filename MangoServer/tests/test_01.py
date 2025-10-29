from django.test import TestCase
from src.auto_test.auto_pytest.models import PytestCase


class SimpleTest(TestCase):
    def test_01(self):
        """简单的文件路径刷新"""
        for i in PytestCase.objects.all():
            i.file_path = i.file_path.replace('\\', '/')
            i.save()
        print("✅ 文件路径刷新完成")
