from django.test import SimpleTestCase

from src.apps.auto_ui.services.element_ai.element_ai_service import ElementAiService
from src.apps.auto_ui.tests.executor.fixtures.mango_mock_lab import (
    BUTTON_ELEMENTS,
    CASE_SCENARIO,
    FIND_TARGETS,
    HEALING_SCENARIOS,
    HEALING_TARGET,
    LAB_URL,
    LIVE_CONTROL_EVENTS,
    PAGE_STEP_SCENARIO,
)
from src.processes.realtime.live_stream.protocol import (
    LiveStreamControlEventValidator,
)


class MangoMockElementFixtureTest(SimpleTestCase):
    def test_components_url_and_button_locators_are_stable(self):
        self.assertEqual(LAB_URL, "http://mock.example.com:8003/#components")
        self.assertGreaterEqual(len(BUTTON_ELEMENTS), 6)
        for key, element in BUTTON_ELEMENTS.items():
            with self.subTest(element=key):
                self.assertTrue(element["test_id"])
                self.assertEqual(
                    element["locator"],
                    f'get_by_test_id("{element["test_id"]}")',
                )
                self.assertEqual(element["operation"], "w_click")

    def test_page_step_and_case_reference_known_fixture_elements(self):
        self.assertEqual(PAGE_STEP_SCENARIO["url"], LAB_URL)
        self.assertEqual(CASE_SCENARIO["url"], LAB_URL)
        self.assertTrue(CASE_SCENARIO["page_steps"])
        for element_key in PAGE_STEP_SCENARIO["steps"]:
            self.assertIn(element_key, BUTTON_ELEMENTS)

    def test_delayed_and_healing_find_targets_use_unique_test_ids(self):
        test_ids = [item["test_id"] for item in FIND_TARGETS.values()]
        self.assertEqual(len(test_ids), len(set(test_ids)))
        self.assertIn("delayed-element", test_ids)
        self.assertIn("healing-interaction-result", test_ids)

    def test_live_element_controls_are_accepted_by_server_protocol(self):
        payloads = {
            "pick_element": {"x": 0.5, "y": 0.5},
            "check_locator": {
                "row_key": "mango-mock-single-click",
                "name": BUTTON_ELEMENTS["single_click"]["name"],
                "locators": [{
                    "exp": 2,
                    "loc": BUTTON_ELEMENTS["single_click"]["locator"],
                }],
            },
            "list_pages": {},
        }
        self.assertEqual(set(LIVE_CONTROL_EVENTS.values()), set(payloads))
        for sequence, event_type in enumerate(LIVE_CONTROL_EVENTS.values(), start=1):
            with self.subTest(event_type=event_type):
                result = LiveStreamControlEventValidator.validate({
                    "event_type": event_type,
                    "sequence": sequence,
                    **payloads[event_type],
                })
                self.assertEqual(result["event_type"], event_type)


class MangoMockHealingContractTest(SimpleTestCase):
    def test_healing_fixture_preserves_baseline_and_current_locator(self):
        self.assertNotEqual(
            HEALING_TARGET["baseline_test_id"],
            HEALING_TARGET["current_test_id"],
        )
        self.assertIn(
            HEALING_TARGET["baseline_test_id"],
            HEALING_TARGET["baseline_locator"],
        )
        self.assertIn(
            HEALING_TARGET["current_test_id"],
            HEALING_TARGET["current_locator"],
        )

    def test_ambiguous_and_missing_candidates_are_rejected(self):
        ambiguous = HEALING_SCENARIOS["ambiguous"]
        missing = HEALING_SCENARIOS["missing"]

        ambiguous_reason = ElementAiService._candidate_reject_reason({
            "verified": ambiguous["verified"],
            "count": ambiguous["candidate_count"],
            "sub": None,
        })
        missing_reason = ElementAiService._candidate_reject_reason({
            "verified": missing["verified"],
            "count": missing["candidate_count"],
        })

        self.assertIn("匹配到多个元素", ambiguous_reason)
        self.assertIn("匹配数量小于1", missing_reason)

    def test_unique_drift_candidates_pass_basic_candidate_gate(self):
        for scenario_name in ("attribute_drift", "relocated"):
            scenario = HEALING_SCENARIOS[scenario_name]
            with self.subTest(scenario=scenario_name):
                reason = ElementAiService._candidate_reject_reason({
                    "verified": scenario["verified"],
                    "count": scenario["candidate_count"],
                })
                self.assertIsNone(reason)
