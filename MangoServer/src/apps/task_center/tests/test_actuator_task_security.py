from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import AuthenticationFailed

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.runtime_center.system_error_event import (
    SystemErrorEventService,
    SystemErrorEventSource,
)
from src.apps.task_center.api.views.actuator_tasks import ActuatorTaskViews
from src.apps.task_center.services.execution.actuator_task_lease import ActuatorTaskLease


class ActuatorTaskSecurityTests(SimpleTestCase):
    def test_actuator_identity_comes_from_authenticated_token(self):
        request = SimpleNamespace(user={
            "username": "actuator_user",
            "client_type": ClientTypeEnum.ACTUATOR.value,
        })

        self.assertEqual(ActuatorTaskViews._actuator_username(request), "actuator_user")

    def test_web_login_token_cannot_pull_actuator_tasks(self):
        request = SimpleNamespace(user={
            "username": "web_user",
            "client_type": ClientTypeEnum.WEB.value,
        })

        with self.assertRaises(AuthenticationFailed):
            ActuatorTaskViews._actuator_username(request)

    def test_task_ack_must_match_user_message_and_dispatch(self):
        marker = ActuatorTaskLease.marker("message-1", "actuator_user", "ui:123")

        self.assertTrue(ActuatorTaskLease.marker_matches(marker, "actuator_user", "message-1", "ui:123"))
        self.assertFalse(ActuatorTaskLease.marker_matches(marker, "other_user", "message-1", "ui:123"))
        self.assertFalse(ActuatorTaskLease.marker_matches(marker, "actuator_user", "message-2", "ui:123"))
        self.assertFalse(ActuatorTaskLease.marker_matches(marker, "actuator_user", "message-1", "ui:456"))

    @patch.object(SystemErrorEventService, 'record')
    def test_actuator_can_report_system_error(self, record):
        request = SimpleNamespace(
            user={
                "username": "actuator_user",
                "client_type": ClientTypeEnum.ACTUATOR.value,
            },
            data={
                "operation": "runtime:socket_consumer",
                "exception_type": "RuntimeError",
                "message": "consumer stopped",
                "traceback": "traceback text",
            },
        )

        ActuatorTaskViews().report_system_error(request)

        record.assert_called_once_with(
            service_name='actuator:actuator_user',
            source=SystemErrorEventSource.ACTUATOR,
            request_path='runtime:socket_consumer',
            exception_type='RuntimeError',
            message='consumer stopped',
            trace='traceback text',
        )
