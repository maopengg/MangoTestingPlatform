from src.apps.user.services.authorization.http_permission_registry import permission_for_view
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.system.api.views.runtime_center import RuntimeCenterViews
from src.apps.system.services.runtime_center.system_error_event import (
    SystemErrorEventService,
    SystemErrorEventSource,
)


class FrontendSystemErrorTests(SimpleTestCase):
    @patch.object(SystemErrorEventService, 'record')
    def test_web_user_can_report_frontend_error(self, record):
        request = SimpleNamespace(
            user={'username': 'web_user'},
            data={
                'operation': 'vue:render @ /#/system/error-record/index',
                'exception_type': 'TypeError',
                'message': 'Cannot read properties of undefined',
                'traceback': 'TypeError: Cannot read properties of undefined',
            },
        )

        RuntimeCenterViews().report_frontend_error(request)

        record.assert_called_once_with(
            service_name='web-console:web_user',
            source=SystemErrorEventSource.FRONTEND,
            request_path='vue:render @ /#/system/error-record/index',
            exception_type='TypeError',
            message='Cannot read properties of undefined',
            trace='TypeError: Cannot read properties of undefined',
        )

    def test_frontend_error_uses_home_permission(self):
        self.assertEqual(
            permission_for_view(RuntimeCenterViews, 'report_frontend_error'),
            'index.home',
        )
