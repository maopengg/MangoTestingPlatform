from django.test import SimpleTestCase

from src.apps.system.api.serializers.cache_data_mutation import CacheDataSerializers
from src.apps.system.enums.cache import SystemConfigManagementLevelEnum
from src.apps.system.models import CacheData
from src.apps.system.services.system_config import (
    API_WORKER_DESIRED_COUNT_DEFAULT,
    API_WORKER_DESIRED_COUNT_KEY,
    SYSTEM_CONFIG_REGISTRY,
    SystemConfigDefinition,
    SystemConfigService,
)


class ConfigManagementLevelTests(SimpleTestCase):
    def test_model_persists_supported_management_levels(self):
        field = CacheData._meta.get_field("management_level")

        self.assertEqual(
            field.default,
            SystemConfigManagementLevelEnum.STANDARD.value,
        )
        self.assertEqual(
            dict(field.choices),
            SystemConfigManagementLevelEnum.obj(),
        )
        self.assertNotIn("is_public", {item.name for item in CacheData._meta.fields})

    def test_internal_configs_are_always_synced_as_level_one(self):
        definition = SystemConfigDefinition(
            key="INTERNAL_TEST_CONFIG",
            describe="系统内部配置",
            group="internal",
            management_level=SystemConfigManagementLevelEnum.INTERNAL.value,
        )

        defaults = SystemConfigService._definition_defaults(definition)

        self.assertEqual(
            defaults["management_level"],
            SystemConfigManagementLevelEnum.INTERNAL.value,
        )

    def test_management_levels_are_limited_to_internal_caution_and_standard(self):
        levels = {item.management_level for item in SYSTEM_CONFIG_REGISTRY}

        self.assertEqual(
            levels,
            {
                SystemConfigManagementLevelEnum.INTERNAL.value,
                SystemConfigManagementLevelEnum.CAUTION.value,
                SystemConfigManagementLevelEnum.STANDARD.value,
            },
        )

    def test_original_settings_page_configs_are_standard_level(self):
        definitions = {item.key: item for item in SYSTEM_CONFIG_REGISTRY}
        original_keys = {
            "SYSTEM_DOMAIN_NAME",
            "SYSTEM_SEND_USER",
            "SYSTEM_EMAIL_HOST",
            "SYSTEM_STAMP_KET",
            "API_TIMEOUT",
            "DATA_FACTORY_VALIDATION_ENVIRONMENTS",
            "SQL_SLOW_QUERY_THRESHOLD_SECONDS",
            "SQL_EXECUTION_RETENTION_DAYS",
            "GUEST_CAN_VIEW_ALL_PROJECT_DATA",
            "UI_FIXED_LOCATOR_RETRY_SECONDS",
            "UI_SMART_LOCATOR_TIMEOUT_SECONDS",
            "AI_PROVIDER_TYPE",
            "AI_API_KEY",
            "AI_BASE_URL",
            "AI_MODEL",
            "AI_TIMEOUT",
            "AI_VISION_PROXY_URL",
            API_WORKER_DESIRED_COUNT_KEY,
        }

        self.assertTrue(original_keys.issubset(definitions))
        self.assertTrue(
            all(
                definitions[key].management_level
                == SystemConfigManagementLevelEnum.STANDARD.value
                for key in original_keys
            )
        )

    def test_api_worker_capacity_is_a_standard_api_setting_with_default_five(self):
        definition = next(
            item
            for item in SYSTEM_CONFIG_REGISTRY
            if item.key == API_WORKER_DESIRED_COUNT_KEY
        )

        self.assertEqual(definition.group, "api")
        self.assertEqual(definition.default_value, API_WORKER_DESIRED_COUNT_DEFAULT)
        self.assertEqual(
            definition.management_level,
            SystemConfigManagementLevelEnum.STANDARD.value,
        )

    def test_management_level_is_read_only_in_settings_serializer(self):
        self.assertTrue(CacheDataSerializers().fields["management_level"].read_only)
