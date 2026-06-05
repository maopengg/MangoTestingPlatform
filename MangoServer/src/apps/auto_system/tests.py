# Create your tests here.
import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError

from src.apps.auto_system.views.file_data import FileDataSerializers
from src.apps.auto_system.service.socket_link.consumer import UIConsumer


class YourTestClass(TestCase):

    def test_your_function(self):
        with open(r'D:\GitCode\uitest\MangoServer\test.json') as f:
            data = json.load(f)
            UIConsumer().u_case_batch_result(data)


class FileDataSerializerTests(SimpleTestCase):

    def test_test_file_allows_empty_upload(self):
        field = FileDataSerializers().fields['test_file']
        empty_docx = SimpleUploadedFile(
            'empty.docx',
            b'',
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

        try:
            field.run_validation(empty_docx)
        except ValidationError as error:
            self.fail(f'空文件应该允许上传，当前校验失败：{error.detail}')
