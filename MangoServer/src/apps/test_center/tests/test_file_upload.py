from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile, TemporaryUploadedFile
from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.test_center.api.views.file_data import FileDataCRUD


class FileUploadTests(SimpleTestCase):
    def test_upload_preserves_file_handle_and_multivalue_fields(self):
        for on_disk in (False, True):
            with self.subTest(on_disk=on_disk):
                upload = (TemporaryUploadedFile('example.bin', 'application/octet-stream', 3, None)
                          if on_disk else SimpleUploadedFile('example.bin', b'abc'))
                try:
                    if on_disk:
                        upload.write(b'abc')
                        upload.seek(0)
                    data = QueryDict('', mutable=True)
                    data['name'] = 'example'
                    data['test_file'] = upload
                    data.setlist('tags', ['first', 'second'])
                    data._mutable = False
                    request = SimpleNamespace(data=data, FILES={'test_file': upload}, user={'id': 4})
                    view = FileDataCRUD()
                    serializer = Mock(data={'id': 1})
                    serializer.is_valid.return_value = True
                    view.serializer = Mock(return_value=serializer)
                    with patch.object(view.model.objects, 'filter', return_value=[]):
                        response = FileDataCRUD.post.__wrapped__(view, request)
                    saved = view.serializer.call_args.kwargs['data']
                    self.assertIs(saved['test_file'], upload)
                    self.assertEqual(saved['test_file'].read(), b'abc')
                    self.assertEqual(saved.getlist('tags'), ['first', 'second'])
                    self.assertEqual(saved['file_size'], 3)
                    self.assertEqual(saved['type'], 0)
                    self.assertEqual(saved['user'], 4)
                    self.assertEqual(saved['update_user'], 4)
                    self.assertNotIn('file_size', data)
                    self.assertNotIn('type', data)
                    serializer.save.assert_called_once()
                    self.assertEqual(response.data['data'], {'id': 1})
                finally:
                    upload.close()
