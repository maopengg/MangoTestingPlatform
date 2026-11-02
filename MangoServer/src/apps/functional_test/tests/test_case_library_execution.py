from src.apps.user.services.http_permission_registry import permission_for_view
# -*- coding: utf-8 -*-
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import resolve
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.functional_test.api.serializers.iteration import FunctionalTestIterationListSerializer
from src.apps.functional_test.api.serializers.plan import (
    FunctionalTestPlanListSerializer,
    FunctionalTestPlanSerializer,
)
from src.apps.functional_test.api.serializers.suite import ManualTestSuiteSerializer, ManualTestSuiteSerializerC
from src.apps.functional_test.api.views.case import ManualTestCaseViews
from src.apps.functional_test.api.views.grid_view import FunctionalCaseGridViewViews
from src.apps.functional_test.api.views.plan import FunctionalTestPlanViews
from src.apps.functional_test.enums import FunctionalCaseStatusEnum, ManualTestSuiteStatusEnum
from src.apps.functional_test.exceptions import FunctionalTestError
from src.apps.functional_test.models import (
    FunctionalTestDefect,
    FunctionalTestDefectCase,
    FunctionalTestIteration,
    FunctionalTestPlan,
    FunctionalTestPlanCase,
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.case_version import ManualTestCaseVersionService
from src.apps.functional_test.services.defect import FunctionalTestDefectService
from src.apps.functional_test.services.execution import FunctionalTestExecutionService
from src.apps.functional_test.services.iteration import FunctionalTestIterationService
from src.apps.functional_test.services.mutation import FunctionalTestMutationService
from src.apps.system.api.views.system_api import SystemViews


class FunctionalTestCaseLibrarySnapshotTests(SimpleTestCase):
    def test_case_asset_status_only_contains_active_lifecycle_states(self):
        self.assertEqual(
            FunctionalCaseStatusEnum.obj(),
            {0: "草稿", 1: "启用", 2: "停用"},
        )
        self.assertEqual(
            dict(ManualTestCase._meta.get_field("status").choices),
            FunctionalCaseStatusEnum.obj(),
        )

    def test_all_category_fields_are_optional(self):
        for field_name in ("category_level_1", "category_level_2", "category_level_3"):
            field = ManualTestCase._meta.get_field(field_name)
            self.assertTrue(field.null)
            self.assertTrue(field.blank)

    def test_case_snapshot_contains_library_fields_and_not_legacy_result(self):
        case = ManualTestCase(
            case_no="FT-0001",
            title="登录成功",
            project_product_id=11,
            module_id=22,
            category_level_1="账号",
            category_level_2="登录",
            priority=1,
            test_types=[0],
            story_refs=["AC-001"],
            test_point="校验正确账号密码登录",
            test_steps=[{"action": "输入账号密码", "expected": "输入成功"}],
            expected_result="进入首页",
            owner_id=33,
            scenario_tags=["smoke_verification"],
        )

        snapshot = FunctionalTestExecutionService.case_snapshot(case)

        self.assertEqual(snapshot["category_level_1"], "账号")
        self.assertEqual(snapshot["test_steps"][0]["action"], "输入账号密码")
        self.assertEqual(snapshot["expected_result"], "进入首页")
        self.assertNotIn("legacy_test_result", snapshot)
        self.assertNotIn("test_result", snapshot)
        self.assertNotIn("legacy_test_result", [field.name for field in ManualTestCase._meta.fields])

    def test_snapshot_is_deep_copy(self):
        case = ManualTestCase(
            case_no="FT-0002",
            title="深拷贝",
            project_product_id=11,
            module_id=22,
            category_level_1="基础",
            priority=1,
            test_types=[0],
            story_refs=[],
            test_point="验证快照隔离",
            test_steps=[{"action": "原始", "expected": "不变"}],
            owner_id=33,
            scenario_tags=[],
        )
        snapshot = FunctionalTestExecutionService.case_snapshot(case)
        snapshot["test_steps"][0]["action"] = "执行中编辑"
        self.assertEqual(case.test_steps[0]["action"], "原始")

    def test_execution_snapshot_contains_api_and_ui_bindings(self):
        case = ManualTestCase(
            case_no="FT-0004",
            title="自动化绑定",
            project_product_id=11,
            module_id=22,
            priority=1,
            test_types=[0],
            story_refs=[],
            test_point="验证自动化绑定快照",
            test_steps=[],
            owner_id=33,
            scenario_tags=[],
        )
        case.prefetched_bindings = [
            ManualTestAutomationBinding(
                automation_type=0,
                automation_case_id=101,
                api_case_id=101,
                automation_case_name="登录 API",
                relation_type=1,
            ),
            ManualTestAutomationBinding(
                automation_type=1,
                automation_case_id=202,
                ui_case_id=202,
                automation_case_name="登录 UI",
                relation_type=1,
            ),
        ]

        snapshot = FunctionalTestExecutionService.case_snapshot(case)

        self.assertEqual(snapshot["automation_bindings"][0]["automation_case_id"], 101)
        self.assertEqual(snapshot["automation_bindings"][0]["automation_case_name"], "登录 API")
        self.assertEqual(snapshot["automation_bindings"][1]["automation_case_id"], 202)

    def test_version_snapshot_contains_library_state(self):
        case = ManualTestCase(
            case_no="FT-0003",
            title="版本快照",
            project_product_id=11,
            module_id=22,
            category_level_1="订单",
            priority=2,
            test_types=[0],
            story_refs=[],
            test_point="验证历史版本",
            test_steps=[{"action": "提交", "expected": "成功"}],
            owner_id=33,
            scenario_tags=[],
            version_no=2,
        )

        snapshot = ManualTestCaseVersionService.snapshot(case)

        self.assertEqual(snapshot["title"], "版本快照")
        self.assertEqual(snapshot["category_level_1"], "订单")
        self.assertEqual(snapshot["test_steps"][0]["action"], "提交")

    def test_version_history_keeps_twenty_snapshots(self):
        self.assertEqual(ManualTestCaseVersionService.HISTORY_LIMIT, 20)

    def test_bulk_update_rejects_non_editable_fields(self):
        updates, errors = FunctionalTestMutationService.normalize_bulk_case_updates([
            {"id": 1, "version_no": 2, "changes": {"project_product": 3}}
        ])

        self.assertEqual(updates, [])
        self.assertIn("project_product", errors["updates[0]"])

    def test_batch_create_endpoint_uses_case_create_permission(self):
        self.assertEqual(
            resolve("/api/functional-test/case/batch-create").func.actions,
            {"post": "batch_create"},
        )
        self.assertEqual(
            permission_for_view(ManualTestCaseViews, "batch_create"),
            "functional.case:add",
        )

    def test_bulk_update_groups_multiple_cell_changes_by_case(self):
        updates, errors = FunctionalTestMutationService.normalize_bulk_case_updates([
            {
                "id": 1,
                "version_no": 2,
                "changes": {
                    "title": "新标题",
                    "priority": 2,
                    "test_types": [0, 1],
                    "owner_id": 33,
                    "project_product_id": 11,
                    "module_id": 22,
                    "scenario_tags": ["smoke_verification"],
                    "automation_status": "automated",
                },
            }
        ])

        self.assertIsNone(errors)
        self.assertEqual(updates[0]["changes"]["title"], "新标题")
        self.assertEqual(updates[0]["changes"]["priority"], 2)
        self.assertEqual(updates[0]["changes"]["test_types"], [0, 1])
        self.assertEqual(updates[0]["changes"]["owner_id"], 33)
        self.assertEqual(updates[0]["changes"]["project_product_id"], 11)
        self.assertEqual(updates[0]["changes"]["module_id"], 22)
        self.assertEqual(updates[0]["changes"]["scenario_tags"], ["smoke_verification"])
        self.assertEqual(updates[0]["changes"]["automation_status"], "automated")


class FunctionalTestPlanValidationTests(SimpleTestCase):
    def test_detail_actions_do_not_use_reserved_viewset_detail_name(self):
        self.assertTrue(callable(FunctionalTestPlanViews.retrieve))

    def test_plan_has_single_execution_endpoints(self):
        self.assertEqual(resolve("/api/functional-test/plan/start").func.actions, {"post": "start"})
        self.assertEqual(resolve("/api/functional-test/plan/finish").func.actions, {"post": "finish"})

    def test_execution_state_is_stored_on_plan_and_plan_case(self):
        self.assertIsNotNone(FunctionalTestPlan._meta.get_field("started_at"))
        self.assertIsNotNone(FunctionalTestPlan._meta.get_field("finished_at"))
        self.assertIsNotNone(FunctionalTestPlanCase._meta.get_field("result"))
        self.assertIsNotNone(FunctionalTestPlanCase._meta.get_field("executor"))
        self.assertIsNotNone(FunctionalTestPlanCase._meta.get_field("execute_time"))

    def test_requirement_plan_requires_requirement(self):
        serializer = FunctionalTestPlanSerializer()
        with self.assertRaises(FunctionalTestError):
            serializer.validate({"scope_type": 0, "project_product": SimpleNamespace(id=1)})

    def test_non_requirement_plan_clears_requirement(self):
        serializer = FunctionalTestPlanSerializer()
        attrs = serializer.validate({
            "scope_type": 2,
            "project_product": SimpleNamespace(id=1),
            "requirement": SimpleNamespace(project_product_id=1),
        })
        self.assertIsNone(attrs["requirement"])

    def test_requirement_plan_binds_concrete_requirement_version(self):
        requirement = SimpleNamespace(project_product_id=1)
        version = SimpleNamespace(project_product_id=1, requirement=requirement)
        attrs = FunctionalTestPlanSerializer().validate({
            "scope_type": 0,
            "project_product": SimpleNamespace(id=1),
            "requirement_version": version,
        })
        self.assertIs(attrs["requirement"], requirement)
        self.assertIsNone(attrs["iteration"])

    def test_sprint_plan_requires_iteration(self):
        with self.assertRaises(FunctionalTestError):
            FunctionalTestPlanSerializer().validate({
                "scope_type": 1,
                "project_product": SimpleNamespace(id=1),
            })

    def test_plan_execution_stats(self):
        instance = SimpleNamespace(
            case_count=10,
            executed_count=8,
            passed_count=6,
            failed_count=1,
            blocked_count=1,
            skipped_count=0,
        )

        stats = FunctionalTestPlanListSerializer.get_execution_stats(instance)

        self.assertEqual(stats["progress"], 80)
        self.assertEqual(stats["pass_rate"], 75)


class FunctionalTestSchedulingAndDefectTests(SimpleTestCase):
    @patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names', return_value={})
    def test_enum_api_exposes_research_quality_status_options(self, environment_names):
        response = SystemViews().enum_api(
            Request(APIRequestFactory().get("/api/system/enum")),
        )
        data = response.data["data"]
        for key in (
                "functional_test_iteration_status",
                "functional_test_requirement_status",
                "manual_test_suite_status",
                "functional_test_defect_source",
                "functional_test_defect_type",
                "functional_test_defect_severity",
                "functional_test_defect_priority",
                "functional_test_defect_status",
                "functional_test_defect_resolution",
        ):
            with self.subTest(key=key):
                self.assertTrue(data[key])

    def test_quality_relation_and_defect_routes_are_exposed(self):
        expected_routes = {
            "/api/functional-test/plan/related": {"get": "related"},
            "/api/functional-test/defect/stats": {"get": "stats"},
            "/api/functional-test/defect/related": {"get": "related"},
            "/api/functional-test/defect/status": {"post": "transition"},
            "/api/functional-test/defect/case/bind": {"post": "bind_cases"},
            "/api/functional-test/defect/case/unbind": {"delete": "unbind_cases"},
            "/api/functional-test/defect/retest-plan": {"post": "create_retest_plan"},
        }
        for path, actions in expected_routes.items():
            with self.subTest(path=path):
                self.assertEqual(resolve(path).func.actions, actions)

    def test_agile_board_routes_are_exposed(self):
        expected_routes = {
            "/api/functional-test/iteration/board": {"get": "board"},
            "/api/functional-test/iteration/cases": {"get": "cases"},
            "/api/functional-test/suite/status": {"post": "transition_status"},
            "/api/functional-test/suite/cases": {"delete": "unlink_cases"},
        }
        for path, actions in expected_routes.items():
            with self.subTest(path=path):
                self.assertEqual(resolve(path).func.actions, actions)

    def test_requirement_version_requires_iteration(self):
        with self.assertRaises(FunctionalTestError):
            ManualTestSuiteSerializer().validate({"owner": SimpleNamespace(id=1)})

    def test_iteration_metrics_are_derived_from_plan_cases(self):
        instance = SimpleNamespace(
            direct_plan_count=1, version_plan_count=2,
            direct_case_count=3, version_case_count=7,
            direct_executed_count=2, version_executed_count=6,
            direct_passed_count=1, version_passed_count=5,
        )
        self.assertEqual(FunctionalTestIterationListSerializer.get_plan_count(instance), 3)
        self.assertEqual(
            FunctionalTestIterationListSerializer.get_test_metrics(instance),
            {"total": 10, "executed": 8, "progress": 80.0, "pass_rate": 75.0},
        )

    def test_requirement_version_metrics_are_derived_from_plan_cases(self):
        metrics = ManualTestSuiteSerializerC.get_test_metrics(SimpleNamespace(
            plan_case_count=5, executed_count=4, passed_count=3,
        ))
        self.assertEqual(metrics, {"total": 5, "executed": 4, "progress": 80.0, "pass_rate": 75.0})

    def test_schedule_is_stored_on_requirement_version_without_extra_schedule_table(self):
        for field_name in (
                "iteration_ref", "development_owner", "planned_start_date",
                "planned_submit_date", "actual_submit_at",
        ):
            self.assertIsNotNone(ManualTestSuite._meta.get_field(field_name))
        self.assertEqual(FunctionalTestIteration._meta.db_table, "functional_test_iteration")

    def test_scheduled_requirement_needs_complete_schedule(self):
        with self.assertRaises(FunctionalTestError):
            FunctionalTestIterationService.validate_schedule(
                iteration=None,
                development_owner_id=None,
                planned_start_date=None,
                planned_submit_date=None,
                status=ManualTestSuiteStatusEnum.SCHEDULED.value,
            )

    def test_schedule_must_stay_inside_iteration(self):
        iteration = SimpleNamespace(start_date=date(2026, 9, 1), end_date=date(2026, 9, 14), status=0)
        with self.assertRaises(FunctionalTestError):
            FunctionalTestIterationService.validate_schedule(
                iteration=iteration,
                development_owner_id=1,
                planned_start_date=date(2026, 8, 31),
                planned_submit_date=date(2026, 9, 5),
                status=ManualTestSuiteStatusEnum.SCHEDULED.value,
            )

    def test_time_progress_is_calculated_not_stored(self):
        self.assertEqual(
            FunctionalTestIterationService._time_progress(
                date(2026, 9, 1), date(2026, 9, 11), date(2026, 9, 6),
            ),
            50,
        )
        self.assertNotIn("time_progress", [field.name for field in ManualTestSuite._meta.fields])

    def test_defect_relation_has_exactly_one_target_constraint(self):
        constraint_names = {item.name for item in FunctionalTestDefectCase._meta.constraints}
        self.assertIn("functional_test_defect_case_exactly_one_target", constraint_names)
        self.assertEqual(FunctionalTestDefect._meta.db_table, "functional_test_defect")

    def test_defect_payload_rejects_duplicate_attachment_ids(self):
        with self.assertRaises(FunctionalTestError):
            FunctionalTestDefectService.validate_attachment_ids([1, 1])


class FunctionalTestGridViewValidationTests(SimpleTestCase):
    def test_grid_config_has_explicit_column_structure(self):
        FunctionalCaseGridViewViews._validate_config({
            "columns": [{"field": "title", "title": "用例标题", "width": 240, "visible": True}],
            "merge_same_cells": True,
        })

    def test_grid_config_rejects_unknown_payload(self):
        with self.assertRaises(FunctionalTestError):
            FunctionalCaseGridViewViews._validate_config({
                "columns": [{"field": "title", "dangerous": True}]
            })
