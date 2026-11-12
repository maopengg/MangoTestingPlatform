from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.auto_api.api.serializers.api_auth_config_mutation import ApiAuthConfigSerializers
from src.apps.auto_api.enums import ApiAuthRefreshModeEnum
from src.apps.auto_api.services.authentication.api_auth_config import ApiAuthConfigService


class ApiAuthConfigMinimumTests(SimpleTestCase):
    def test_service_rejects_refresh_margin_below_ten_minutes(self):
        errors = ApiAuthConfigService.validate_payload(
            None,
            {
                "refresh_mode": ApiAuthRefreshModeEnum.PASSIVE.value,
                "token_ttl": 60,
                "refresh_margin": 9,
            },
        )

        self.assertEqual(errors["refresh_margin"], ["提前刷新时间不能少于10分钟"])

    def test_service_accepts_ten_minute_refresh_margin(self):
        errors = ApiAuthConfigService.validate_payload(
            None,
            {
                "refresh_mode": ApiAuthRefreshModeEnum.PASSIVE.value,
                "token_ttl": 60,
                "refresh_margin": 10,
            },
        )

        self.assertNotIn("refresh_margin", errors)

    def test_rest_serializer_rejects_refresh_margin_below_ten_minutes(self):
        serializer = ApiAuthConfigSerializers()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate(
                {
                    "refresh_mode": ApiAuthRefreshModeEnum.PASSIVE.value,
                    "token_ttl": 60,
                    "refresh_margin": 9,
                }
            )

    def test_rest_serializer_accepts_ten_minute_refresh_margin(self):
        serializer = ApiAuthConfigSerializers()

        attrs = serializer.validate(
            {
                "refresh_mode": ApiAuthRefreshModeEnum.PASSIVE.value,
                "token_ttl": 60,
                "refresh_margin": 10,
            }
        )

        self.assertEqual(attrs["refresh_margin"], 10)
