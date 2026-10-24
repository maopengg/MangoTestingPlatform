from django.test import SimpleTestCase

from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter


class ApiCaseOptionalFieldValidationTests(SimpleTestCase):
    def test_api_case_accepts_default_empty_configuration(self):
        case = ApiCase(
            project_product_id=1,
            module_id=1,
            case_people_id=1,
            name="MCP 空配置用例",
        )

        case.full_clean(exclude=["project_product", "module", "case_people"])

        self.assertIsNone(case.case_flow)
        self.assertEqual(case.parametrize, [])
        self.assertEqual(case.scenario_tags, [])
        self.assertEqual(case.front_custom, [])
        self.assertEqual(case.front_sql, [])
        self.assertEqual(case.front_headers, [])
        self.assertEqual(case.front_public, [])
        self.assertEqual(case.front_auth_config, [])
        self.assertEqual(case.posterior_sql, [])

    def test_api_case_scenario_accepts_default_empty_configuration(self):
        scenario = ApiCaseDetailedParameter(
            case_detailed_id=1,
            name="MCP 空配置场景",
        )

        scenario.full_clean(exclude=["case_detailed"])

        self.assertEqual(scenario.headers, [])
        self.assertEqual(scenario.front_sql, [])
        self.assertEqual(scenario.ass_general, [])
        self.assertEqual(scenario.ass_sql, [])
        self.assertEqual(scenario.ass_jsonpath, [])
        self.assertEqual(scenario.posterior_sql, [])
        self.assertEqual(scenario.posterior_response, [])
        self.assertEqual(scenario.posterior_response_text, [])
        self.assertEqual(scenario.posterior_file, {})
