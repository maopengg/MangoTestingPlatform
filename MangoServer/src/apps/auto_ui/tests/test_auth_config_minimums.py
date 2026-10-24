from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.auto_ui.api.serializers.ui_auth_config_mutation import UiAuthConfigSerializers
from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthTypeEnum
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.services.auth_config import UiAuthConfigService


class UiAuthConfigMinimumTests(SimpleTestCase):
    def _payload(self, expire_notice_minutes: int) -> dict:
        return {
            "test_env": 0,
            "auth_type": UiAuthTypeEnum.MANUAL.value,
            "refresh_mode": UiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
            "notice_group": 1,
            "token_ttl": 60,
            "expire_notice_minutes": expire_notice_minutes,
        }

    def test_service_rejects_notice_margin_below_ten_minutes(self):
        with self.assertRaises(AutoUiError):
            UiAuthConfigService._normalize(None, self._payload(9))

    def test_service_accepts_ten_minute_notice_margin(self):
        attrs = UiAuthConfigService._normalize(None, self._payload(10))

        self.assertEqual(attrs["expire_notice_minutes"], 10)

    def test_rest_serializer_rejects_notice_margin_below_ten_minutes(self):
        serializer = UiAuthConfigSerializers()
        attrs = self._payload(9)
        attrs["notice_group"] = SimpleNamespace(project_id=1)

        with self.assertRaises(serializers.ValidationError):
            serializer.validate(attrs)

    def test_rest_serializer_accepts_ten_minute_notice_margin(self):
        serializer = UiAuthConfigSerializers()
        attrs = self._payload(10)
        attrs["notice_group"] = SimpleNamespace(project_id=1)

        result = serializer.validate(attrs)

        self.assertEqual(result["expire_notice_minutes"], 10)
