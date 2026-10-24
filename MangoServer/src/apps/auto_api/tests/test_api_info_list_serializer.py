from types import SimpleNamespace

from django.test import SimpleTestCase

from src.apps.auto_api.api.serializers.api_info import ApiInfoListSerializersC
from src.apps.auto_api.api.views.api_info import ApiInfoCRUD


class ApiInfoListSerializerTests(SimpleTestCase):

    def test_id_filter_still_uses_publication_state_serializer(self):
        view = ApiInfoCRUD()
        view.request = SimpleNamespace(method='GET', query_params={'id': '6'})

        self.assertIs(view.get_serializer_class(), ApiInfoListSerializersC)
