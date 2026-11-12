from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_case import ApiCaseViews
from src.apps.auto_api.services.api_case.copying import ApiCaseCopyService
from src.common.responses.response_msg import RESPONSE_MSG_0009, RESPONSE_MSG_0210


class ApiCaseCopyViewTests(SimpleTestCase):
    def test_copy_uses_shared_operator_resolution_for_supported_user_contexts(self):
        for user in ({'id': 7}, SimpleNamespace(user_obj=SimpleNamespace(id=7)), SimpleNamespace(id=7)):
            with self.subTest(user_type=type(user).__name__):
                view = ApiCaseViews()
                request = SimpleNamespace(data={'case_id': '21'}, user=user)
                copied = SimpleNamespace(id=22)
                with patch.object(view, '_has_case_scope', return_value=True) as scope, \
                        patch.object(ApiCaseCopyService, 'copy', return_value=copied) as copy, \
                        patch.object(view, 'serializer_class') as serializer:
                    serializer.return_value.data = {'id': 22}
                    response = view.copy_case(request)
                scope.assert_called_once_with(request, '21')
                copy.assert_called_once_with(21, operator_id=7)
                serializer.assert_called_once_with(instance=copied)
                self.assertEqual(response.data['code'], RESPONSE_MSG_0009[0])
                self.assertEqual(response.data['data'], {'id': 22})

    def test_copy_outside_scope_is_rejected_without_creating_case(self):
        view = ApiCaseViews()
        request = SimpleNamespace(data={'case_id': '21'}, user={'id': 7})
        with patch.object(view, '_has_case_scope', return_value=False), \
                patch.object(ApiCaseCopyService, 'copy') as copy:
            response = view.copy_case(request)
        copy.assert_not_called()
        self.assertEqual(response.data['code'], RESPONSE_MSG_0210[0])
