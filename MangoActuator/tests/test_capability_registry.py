import os
import unittest
from unittest.mock import patch

from src.services.capabilities import CapabilityRegistry
from src.services.capabilities.registry import CAPABILITY_DEFINITIONS
from src.services.ui.case_concurrency import UiCaseConcurrency


class CapabilityRegistryTest(unittest.TestCase):
    def tearDown(self):
        CapabilityRegistry.invalidate()
        UiCaseConcurrency.reset()

    def test_default_profile_does_not_define_api_capability(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertNotIn("api", CapabilityRegistry.enabled_codes())
            self.assertEqual(CapabilityRegistry.enabled_codes(), {"pytest", "web_ui", "perf"})

    def test_web_ui_defaults_to_single_live_workspace_slot(self):
        definition = CAPABILITY_DEFINITIONS["web_ui"]
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(definition.default_capacity, 1)
            self.assertEqual(CapabilityRegistry._configured_capacity(definition), 1)

    def test_legacy_executor_type_only_selects_expected_capabilities(self):
        with patch.dict(os.environ, {"EXECUTOR_TYPE": "pytest_web"}, clear=True):
            self.assertEqual(CapabilityRegistry.enabled_codes(), {"pytest", "web_ui"})

    def test_legacy_profile_name_remains_compatible_during_rollout(self):
        with patch.dict(os.environ, {"MANGO_ACTUATOR_PROFILE": "android_ui"}, clear=True):
            self.assertEqual(CapabilityRegistry.enabled_codes(), {"android_ui"})

    def test_environment_profile_overrides_persisted_install_profile(self):
        with (
            patch.dict(os.environ, {"MANGO_ACTUATOR_PROFILE": "pytest"}, clear=True),
            patch.object(
                CapabilityRegistry,
                "_local_config",
                return_value={"profile": "android", "enabled_capabilities": ["android_ui"]},
            ),
        ):
            self.assertEqual(CapabilityRegistry.enabled_codes(), {"pytest"})

    def test_task_capabilities_use_and_compatible_runtime_mapping(self):
        self.assertEqual(CapabilityRegistry.required_capabilities("perf_execution"), ["perf"])
        self.assertEqual(
            CapabilityRegistry.required_capabilities(
                "ui_case", {"func_args": {"type": 3}},
            ),
            ["android_ui"],
        )
        self.assertEqual(
            CapabilityRegistry.required_capabilities(
                "ui_case", {"func_args": {"type": 4}},
            ),
            ["ios_ui"],
        )

    def test_generic_ui_command_requires_runtime_capability(self):
        self.assertEqual(
            CapabilityRegistry.required_capabilities(
                "executor_command",
                {"func_name": "u_page_scan", "func_args": {"data": {"client_type": 4}}},
            ),
            ["ios_ui"],
        )

    def test_api_task_does_not_define_an_independent_capability(self):
        self.assertEqual(CapabilityRegistry.required_capabilities("api_execution", {}), [])

    def test_live_stream_transport_commands_do_not_consume_web_ui_capacity(self):
        for func_name in ("u_live_stream_start", "u_live_stream_stop"):
            with self.subTest(func_name=func_name):
                self.assertEqual(
                    CapabilityRegistry.required_capabilities(
                        "live_control",
                        {"func_name": func_name, "func_args": {}},
                    ),
                    [],
                )

    def test_ui_case_capacity_uses_browser_parallel_configuration(self):
        with (
            patch.object(CapabilityRegistry, "snapshot", return_value={
                "web_ui": type("Status", (), {"ready": True, "capacity": 1})(),
            }),
            patch(
                "src.services.ui.case_concurrency.SetConfig.get_web_parallel",
                return_value=6,
            ),
        ):
            capacities = CapabilityRegistry.available_task_type_capacities()

        self.assertEqual(capacities["ui_case"], 6)
