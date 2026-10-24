import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.ai.agent.api_automation.agent import ApiAutomationAgent
from src.apps.ai.agent.api_automation.executor import ApiAutomationExecutor
from src.apps.ai.agent.api_automation.skill_contract import ApiAutomationSkillContractCompiler
from src.apps.ai.agent.api_automation.tool_catalog import ApiAutomationToolStageCatalog
from src.apps.ai.agent.functional_case.coverage_checker import FunctionalCaseCoverageChecker
from src.apps.ai.exceptions import AiError
from src.apps.ai.services.agent.mcp.tool_filter import AgentMcpToolFilter
from src.apps.ai.services.core import McpService
from src.apps.ai.services.harness.definition import DEFINITIONS
from src.apps.ai.services.harness.regression import HarnessRegressionGate
from src.apps.functional_test.management.commands.migrate_functional_test_hierarchy import \
    Command as HierarchyMigrationCommand
from src.apps.test_center.api.serializers.product_module_mutation import ProductModuleSerializers
from src.apps.test_center.exceptions import TestCenterError
from version_migration_scripts.v_7_0_3_2026_07_17_product_module import _upgrade_module_hierarchy


def ai_json(payload):
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(payload, ensure_ascii=False),
                }
            }
        ]
    }


class AgentHarnessRegressionTests(SimpleTestCase):
    def test_fixed_agent_definitions_pass_the_activation_gate(self):
        for agent_key, definition in DEFINITIONS.items():
            payload = dict(definition)
            payload.pop("version", None)
            report = HarnessRegressionGate.evaluate(agent_key, payload)
            self.assertTrue(report["passed"], report)

    def test_activation_gate_rejects_missing_required_stage(self):
        definition = dict(DEFINITIONS["functional_case"])
        definition.pop("version", None)
        definition["workflow_schema"] = {
            "steps": definition["workflow_schema"]["steps"][:-1]
        }

        report = HarnessRegressionGate.evaluate("functional_case", definition)

        self.assertFalse(report["passed"])
        self.assertIn("工作流阶段、顺序或数量与固定回归集不一致", report["findings"])


class FunctionalCaseTraceabilityTests(SimpleTestCase):
    requirement_model = {
        "acceptance_criteria": [
            {"criterion_id": "AC-001", "description": "允许创建订单"},
            {"criterion_id": "AC-002", "description": "无权限时拒绝创建"},
        ]
    }
    coverage_matrix = {"criteria": []}

    @patch("src.apps.ai.agent.functional_case.coverage_checker.AgentModelGateway.json_chat")
    def test_traceability_gate_rejects_missing_or_unknown_acceptance_refs(self, json_chat):
        json_chat.return_value = ai_json(
            {
                "passed": True,
                "score": 100,
                "covered_criterion_ids": [],
                "missing_criterion_ids": [],
                "partial_criterion_ids": [],
                "dimension_summary": {},
                "findings": [],
            }
        )
        payload = {
            "cases": [
                {
                    "case_no": "FT-0001",
                    "title": "创建订单",
                    "story_refs": ["AC-999"],
                    "acceptance_source": "",
                    "source_text": "",
                }
            ]
        }

        report = FunctionalCaseCoverageChecker.evaluate_final_coverage(
            generated_payload=payload,
            requirement_model=self.requirement_model,
            coverage_matrix=self.coverage_matrix,
            user_instruction="",
            skill=None,
            ai_role=None,
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["missing_criterion_ids"], ["AC-001", "AC-002"])
        self.assertTrue(any(item["type"] == "traceability" for item in report["findings"]))

    @patch("src.apps.ai.agent.functional_case.coverage_checker.AgentModelGateway.json_chat")
    def test_traceability_gate_accepts_complete_deterministic_evidence(self, json_chat):
        json_chat.return_value = ai_json(
            {
                "passed": True,
                "score": 100,
                "covered_criterion_ids": ["AC-001", "AC-002"],
                "missing_criterion_ids": [],
                "partial_criterion_ids": [],
                "dimension_summary": {},
                "findings": [],
            }
        )
        payload = {
            "cases": [
                {
                    "case_no": "FT-0001",
                    "title": "创建订单",
                    "story_refs": ["AC-001"],
                    "acceptance_source": "订单创建验收标准",
                    "source_text": "用户提交合法订单后创建成功",
                },
                {
                    "case_no": "FT-0002",
                    "title": "无权限创建订单",
                    "story_refs": ["AC-002"],
                    "acceptance_source": "订单权限规则",
                    "source_text": "无创建权限的用户应被拒绝",
                },
            ]
        }

        report = FunctionalCaseCoverageChecker.evaluate_final_coverage(
            generated_payload=payload,
            requirement_model=self.requirement_model,
            coverage_matrix=self.coverage_matrix,
            user_instruction="",
            skill=None,
            ai_role=None,
        )

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["missing_criterion_ids"], [])


class ApiAutomationContractTests(SimpleTestCase):
    def test_platform_completion_capabilities_cannot_be_removed_by_skill(self):
        skill = SimpleNamespace(id=7)
        contract = ApiAutomationSkillContractCompiler.normalize(
            {
                "required_capabilities": ["data_factory"],
                "forbidden_capabilities": ["assertion", "execution"],
            },
            skill,
        )

        self.assertEqual(
            contract["required_capabilities"][:4],
            ["api_info", "api_case", "assertion", "execution"],
        )
        self.assertIn("data_factory", contract["required_capabilities"])
        self.assertNotIn("assertion", contract["forbidden_capabilities"])
        self.assertNotIn("execution", contract["forbidden_capabilities"])

    def test_nested_mcp_business_failure_is_not_reported_as_success(self):
        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "success": False,
                            "message": "创建 API Case 失败",
                            "error_code": "CREATE_API_CASE_FAILED",
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
            "isError": False,
        }

        self.assertFalse(McpService.is_tool_call_success(result))

    def test_normal_mcp_text_result_is_successful(self):
        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"success": True, "data": {"api_case_id": 108}}),
                }
            ],
            "isError": False,
        }

        self.assertTrue(McpService.is_tool_call_success(result))

    def test_api_automation_tool_filter_keeps_all_selected_mcp_tools(self):
        tools = [
            SimpleNamespace(name="get_api_case_detail_full", write_operation=False),
            SimpleNamespace(name="delete_api_case", write_operation=True),
            SimpleNamespace(name="cleanup_data_factory_execution", write_operation=True),
        ]

        self.assertEqual(
            AgentMcpToolFilter.filter_for_api_automation(tools, existing_api_case_id=108),
            tools,
        )

    def test_planner_catalog_contains_tool_meaning_risk_and_schema_fingerprint(self):
        tool = SimpleNamespace(
            name="create_api_case",
            title="创建 API 用例",
            description="在测试平台创建 API Case",
            server_id=3,
            risk_level=2,
            write_operation=True,
            require_confirm=True,
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"case_id": {"type": "integer"}}},
        )

        catalog = ApiAutomationToolStageCatalog.catalog_for_tools({"create_api_case": tool})
        stage = next(item for item in catalog if item["stage"] == "create_or_update_case")
        summary = stage["available_tools"][0]

        self.assertEqual(summary["name"], "create_api_case")
        self.assertEqual(summary["description"], "在测试平台创建 API Case")
        self.assertEqual(summary["risk_level"], 2)
        self.assertTrue(summary["write_operation"])
        self.assertEqual(len(summary["schema_hash"]), 64)

    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed")
    def test_api_case_asset_gate_rejects_missing_step(self, case_details):
        case_details.return_value.select_related.return_value.filter.return_value = []

        with self.assertRaisesRegex(AiError, "没有步骤"):
            ApiAutomationExecutor.validate_api_case_assertions(108)

    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed_parameter")
    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed")
    def test_api_case_asset_gate_rejects_missing_scenario(self, case_details, parameters):
        case_details.return_value.select_related.return_value.filter.return_value = [
            SimpleNamespace(id=1, api_info=None)]
        parameters.return_value.filter.return_value = []

        with self.assertRaisesRegex(AiError, "没有场景参数"):
            ApiAutomationExecutor.validate_api_case_assertions(108)

    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed_parameter")
    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed")
    def test_api_case_asset_gate_rejects_zero_assertions(self, case_details, parameters):
        case_details.return_value.select_related.return_value.filter.return_value = [
            SimpleNamespace(id=1, api_info=None)]
        parameters.return_value.filter.return_value = [
            SimpleNamespace(
                ass_jsonpath=[],
                ass_general=[],
                ass_json_all=None,
                ass_text_all="",
                ass_schema=None,
            )
        ]

        with self.assertRaisesRegex(AiError, "没有配置任何断言"):
            ApiAutomationExecutor.validate_api_case_assertions(108)

    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed_parameter")
    @patch("src.apps.ai.agent.api_automation.executor.ApiQuerySelector.api_case_detailed")
    def test_api_case_asset_gate_accepts_real_assertion(self, case_details, parameters):
        case_details.return_value.select_related.return_value.filter.return_value = [
            SimpleNamespace(id=1, api_info=None)]
        parameters.return_value.filter.return_value = [
            SimpleNamespace(
                ass_jsonpath=[{"path": "$.code", "expected": 200}],
                ass_general=[],
                ass_json_all=None,
                ass_text_all="",
                ass_schema=None,
            )
        ]

        report = ApiAutomationExecutor.validate_api_case_assertions(108)

        self.assertEqual(report["step_count"], 1)
        self.assertEqual(report["scenario_count"], 1)
        self.assertEqual(report["total_assertion_count"], 1)

    @patch("src.apps.ai.agent.api_automation.agent_parts.validation.ApiQuerySelector.api_case")
    def test_post_validation_rejects_replacing_bound_api_case_id(self, cases):
        cases.return_value.filter.return_value.exists.return_value = True
        task = SimpleNamespace(id=1)
        manual_case = SimpleNamespace(id=2)

        with self.assertRaisesRegex(AiError, "必须覆盖旧 ID"):
            ApiAutomationAgent.post_validate_plan(
                task,
                manual_case,
                {"existing_api_case_id": 108},
                {"api_case_id": 109},
                {},
            )


class FunctionalTestHierarchyTests(SimpleTestCase):
    @patch("version_migration_scripts.v_7_0_3_2026_07_17_product_module.ProductModule.objects")
    def test_version_7_0_3_upgrade_creates_real_parent_nodes(self, module_objects):
        module = SimpleNamespace(
            id=10,
            project_product_id=1,
            name="新增订单类型",
            superior_module_1="订单管理",
            superior_module_2="系统配置",
        )
        module_objects.create.side_effect = [
            SimpleNamespace(id=101),
            SimpleNamespace(id=102),
        ]
        report = {
            "already_migrated": False,
            "root_candidates": {},
            "level_two_candidates": {},
            "required_roots": {(1, "订单管理")},
            "required_level_two": {(1, "订单管理", "系统配置")},
        }

        stats = _upgrade_module_hierarchy([module], report)

        self.assertEqual(stats["created_level_one_count"], 1)
        self.assertEqual(stats["created_level_two_count"], 1)
        self.assertEqual(stats["updated_module_count"], 1)
        module_objects.filter.assert_called_once_with(id=10)
        module_objects.filter.return_value.update.assert_called_once_with(
            parent_id=102,
            level=3,
        )

    @patch("version_migration_scripts.v_7_0_3_2026_07_17_product_module.ProductModule.objects")
    def test_version_7_0_3_upgrade_skips_completed_hierarchy(self, module_objects):
        stats = _upgrade_module_hierarchy(
            [SimpleNamespace(id=1)],
            {"already_migrated": True},
        )

        self.assertTrue(stats["already_migrated"])
        self.assertEqual(stats["updated_module_count"], 0)
        module_objects.create.assert_not_called()
        module_objects.filter.assert_not_called()

    def test_legacy_paths_are_preflighted_into_real_parent_nodes(self):
        modules = [
            SimpleNamespace(
                id=10,
                project_product_id=1,
                name="订单类型",
                superior_module_1="订单管理",
                superior_module_2="系统配置",
                level=None,
                parent_id=None,
            ),
            SimpleNamespace(
                id=11,
                project_product_id=1,
                name="订单列表",
                superior_module_1="订单管理",
                superior_module_2="",
                level=None,
                parent_id=None,
            ),
        ]

        report = HierarchyMigrationCommand.preflight(modules)

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["required_roots"], {(1, "订单管理")})
        self.assertEqual(report["required_level_two"], {(1, "订单管理", "系统配置")})
        self.assertEqual(report["new_parent_estimate"], 2)

    def test_preflight_rejects_second_level_without_first_level(self):
        module = SimpleNamespace(
            id=12,
            project_product_id=1,
            name="异常节点",
            superior_module_1="",
            superior_module_2="孤立二级",
            level=None,
            parent_id=None,
        )

        report = HierarchyMigrationCommand.preflight([module])

        self.assertFalse(report["passed"])
        self.assertTrue(any("只有二级旧路径" in item for item in report["findings"]))

    @patch("src.apps.test_center.api.serializers.product_module_mutation.ProductModule.objects.filter")
    def test_module_serializer_derives_level_from_real_parent(self, module_filter):
        module_filter.return_value.exists.return_value = False
        module_filter.return_value.exclude.return_value.exists.return_value = False
        parent = SimpleNamespace(id=1, name="一级模块", project_product_id=9, level=1, parent=None)
        project_product = SimpleNamespace(id=9)
        instance = SimpleNamespace(
            id=2,
            project_product_id=9,
            project_product=project_product,
            parent=parent,
            level=2,
            name="旧名称",
            children=SimpleNamespace(exists=lambda: False),
        )

        result = ProductModuleSerializers(instance=instance).validate(
            {
                "name": "二级模块",
                "project_product": project_product,
                "parent": parent,
            }
        )

        self.assertEqual(result["level"], 2)

    def test_module_serializer_rejects_cross_product_parent(self):
        parent = SimpleNamespace(id=1, project_product_id=8, level=1, parent=None)
        project_product = SimpleNamespace(id=9)

        instance = SimpleNamespace(id=2, project_product_id=9, level=2)
        with self.assertRaises(TestCenterError):
            ProductModuleSerializers(instance=instance).validate(
                {
                    "name": "非法模块",
                    "project_product": project_product,
                    "parent": parent,
                }
            )

    def test_module_serializer_rejects_more_than_three_levels(self):
        parent = SimpleNamespace(id=3, project_product_id=9, level=3, parent=None)
        project_product = SimpleNamespace(id=9)

        instance = SimpleNamespace(id=4, project_product_id=9, level=3)
        with self.assertRaises(TestCenterError):
            ProductModuleSerializers(instance=instance).validate(
                {
                    "name": "第四级模块",
                    "project_product": project_product,
                    "parent": parent,
                }
            )
