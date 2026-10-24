import json
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test.utils import override_settings
from mangotools.perf.k6_script import K6_SCRIPT_SOURCE
from pydantic import ValidationError

from src.apps.perf.api.serializers.run import PerfRunListSerializer
from src.apps.perf.api.urls import urlpatterns
from src.apps.perf.api.views.run import PerfRunViews
from src.apps.perf.api.views.scenario import PerfScenarioListSerializer, PerfScenarioViews, PerfScenarioWriteSerializer
from src.apps.perf.enums import PerfLoadTypeEnum, PerfRunStatusEnum
from src.apps.perf.exceptions import PerfError
from src.apps.perf.formatters import PERF_DATETIME_FORMAT, format_perf_datetime, format_perf_row_datetimes
from src.apps.perf.models import PerfMetricInterval, PerfRun, PerfScenario
from src.apps.perf.schemas.execution import PerfExecutorPolicy, PerfMetricBatch, PerfScenarioIR
from src.apps.perf.services.compiler import (
    PerfScenarioCompiler,
    ensure_required_scenario_components,
    extract_secrets,
    redact_secrets,
    snapshot_hash,
)
from src.apps.perf.services.datetime_utils import normalize_perf_datetime
from src.apps.perf.services.execution import PerfExecutionService
from src.apps.perf.services.finalize import PerfFinalizeService, _json_number
from src.apps.perf.services.functions import PERF_FUNCTION_ARGUMENTS, collect_perf_functions
from src.apps.perf.services.load_stage import PerfLoadStageService
from src.apps.perf.services.metrics import PerfMetricService
from src.apps.perf.services.performance_goal import PerfPerformanceGoalService
from src.apps.perf.services.scenario_configuration import PerfScenarioConfigurationService
from src.apps.perf.services.secrets import PerfSecretService
from src.apps.perf.services.source_api import PerfSourceCaseService
from src.common.testing import ObtainTestData, get_data_method_info


class PerfSchemaTests(SimpleTestCase):
    def test_capture_download_requires_run_scoped_node_and_expected_artifact_path(self):
        node = SimpleNamespace(result_summary={"capture": {
            "status": "uploaded", "path": "mango-file/perf/capture/perf-run-7-node-9.csv",
        }})
        with (
            patch.object(PerfRunViews, "_get"),
            patch("src.apps.perf.api.views.run.PerfRunNode.objects.filter") as filter_nodes,
            patch("src.apps.perf.api.views.run.ExecutionArtifactService.public_url",
                  return_value="https://example.com/capture.csv"),
        ):
            filter_nodes.return_value.only.return_value.first.return_value = node
            response = PerfRunViews().capture_download(SimpleNamespace(user=None), pk=7, node_id=9)
        self.assertEqual(response.data["data"]["name"], "perf-run-7-node-9.csv")
        self.assertEqual(response.data["data"]["url"], "https://example.com/capture.csv")
        filter_nodes.assert_called_once_with(id=9, run_id=7)

    def test_script_preview_returns_shared_k6_template_and_redacted_snapshot(self):
        scenario = SimpleNamespace(project_product_id=1, version=4)
        snapshot = {"steps": [{"request": {"headers": {"Authorization": "***"}}}]}
        with (
            patch("src.apps.perf.api.views.scenario.PerfScenario.objects.select_related") as select_related,
            patch("src.apps.perf.api.views.scenario.ensure_perf_data_scope"),
            patch("src.apps.perf.api.views.scenario.PerfScenarioCompiler.compile", return_value=(snapshot, "digest")),
        ):
            select_related.return_value.filter.return_value.first.return_value = scenario
            response = PerfScenarioViews().script_preview(SimpleNamespace(user=None), pk=1)
        preview = response.data["data"]
        self.assertEqual(preview["script"], K6_SCRIPT_SOURCE)
        self.assertEqual(preview["scenario_version"], 4)
        self.assertEqual(preview["snapshot_hash"], "digest")
        self.assertEqual(json.loads(preview["snapshot"]), snapshot)

    def test_performance_data_methods_are_visible_and_generate_values(self):
        methods = next(item for item in get_data_method_info() if item["value"] == "performance")
        names = {method["value"] for group in methods["children"] for method in group["children"]}
        self.assertEqual(names, set(PERF_FUNCTION_ARGUMENTS))
        data = ObtainTestData()
        self.assertEqual(len(data.replace("${{perf_uuid()}}")), 36)
        self.assertEqual(len(data.replace("${{perf_random_digits(8)}}")), 8)
        self.assertEqual(len(data.replace("${{perf_random_string(16)}}")), 16)

    def test_performance_functions_compile_from_case_without_pre_generated_rows(self):
        expressions = {
            "id": "${{perf_snowflake_id()}}",
            "trace": "${{perf_uuid()|request_id}}",
            "body": "order-${{perf_random_string(16)}}",
            "negative": "${{perf_random_int(-4, 4)}}",
            "prefix": "${{perf_unique_string(order)}}",
        }
        functions = collect_perf_functions(expressions)
        self.assertEqual(len(functions), 5)
        self.assertEqual(next(item for item in functions if item["name"] == "perf_uuid")["cache_key"], "request_id")
        self.assertEqual(next(item for item in functions if item["name"] == "perf_random_int")["args"],
                         {"left": -4, "right": 4})
        preview = PerfSourceCaseService._preview_payload({
            "api_case": {"front_custom": [{"key": "id", "value": expressions["id"]}]},
            "api_case_detailed": [],
        })
        self.assertTrue(preview["compatible"])

    def test_performance_functions_reject_unsupported_and_unsafe_calls(self):
        for expression in (
                "${{number_snowflake_id()}}",
                "${{perf_random_string(300)}}",
                "${{perf_random_int(-9007199254740991, 9007199254740991)}}",
                "${{perf_uuid(perf_random_int())}}",
        ):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                collect_perf_functions({"value": expression})

    def test_operator_facing_perf_datetimes_use_second_precision(self):
        value = datetime(2026, 9, 1, 11, 51, 34, 328570)
        expected = "2026-09-01 11:51:34"
        self.assertEqual(format_perf_datetime(value), expected)
        self.assertIsNone(format_perf_datetime(None))
        self.assertEqual(format_perf_row_datetimes({"update_time": value, "id": 3}), {
            "update_time": expected, "id": 3,
        })
        for serializer_class, fields in (
                (PerfScenarioWriteSerializer, ("create_time", "update_time")),
                (PerfScenarioListSerializer, ("create_time", "update_time")),
                (PerfRunListSerializer, ("create_time", "update_time", "started_at", "finished_at")),
        ):
            serializer = serializer_class()
            for field_name in fields:
                field = serializer.fields[field_name]
                self.assertEqual(field.format, PERF_DATETIME_FORMAT)
                self.assertEqual(field.to_representation(value), expected)

    def test_json_consistency_compiles_to_subset_contains(self):
        result = PerfScenarioCompiler._compile_parameter(
            step={
                "id": 1,
                "api_info_id": 2,
                "api_info_revision_id": 3,
                "api_info_snapshot": {"checksum": "checksum"},
            },
            parameter={"id": 4, "name": "查询", "ass_json_all": {"code": 0}},
            api_payload={"protocol_type": "http", "body_type": "none"},
            sort=0,
        )

        self.assertEqual(result["checks"][0]["operator"], "contains")
        self.assertEqual(result["checks"][0]["expected"], {"code": 0})

    @override_settings(USE_TZ=False, TIME_ZONE="Asia/Shanghai")
    def test_executor_utc_datetime_is_normalized_for_naive_database(self):
        value = normalize_perf_datetime(datetime(2026, 8, 31, 4, 0, tzinfo=timezone.utc))

        self.assertIsNone(value.tzinfo)
        self.assertEqual(value, datetime(2026, 8, 31, 12, 0))

    def test_executor_selection_is_required_and_exact(self):
        with self.assertRaises(PerfError) as missing:
            PerfExecutionService._validate_executor_selection(2, [])
        self.assertIn("必须选择 2 个执行器，当前选择 0 个", missing.exception.msg)

        with self.assertRaises(PerfError):
            PerfExecutionService._validate_executor_selection(2, ["user:1", "user:1"])

        self.assertEqual(
            PerfExecutionService._validate_executor_selection(2, ["user:1", "user:2"]),
            ["user:1", "user:2"],
        )

    def test_all_failed_nodes_make_the_run_failed(self):
        self.assertEqual(PerfFinalizeService._final_status(0, 1), "failed")
        self.assertEqual(PerfFinalizeService._final_status(1, 1), "partial")
        self.assertEqual(PerfFinalizeService._final_status(1, 0), "completed")

    def test_finalize_summary_numbers_are_json_serializable(self):
        from decimal import Decimal
        import json

        value = {"p95_ms": _json_number(Decimal("12.50")), "request_count": 3}
        self.assertEqual(json.loads(json.dumps(value)), {"p95_ms": 12.5, "request_count": 3})

    def test_source_case_preview_exposes_flow_and_compatibility(self):
        preview = PerfSourceCaseService._preview_payload({
            "api_case": {"case_flow": "登录 -> 查询"},
            "dependencies": {"data_factory_configs": []},
            "api_case_detailed": [{
                "id": 1, "logical_id": "step-1", "api_info_id": 7,
                "api_case_detailed_parameter": [{"id": 2, "name": "登录", "protocol_type": "http", "body_type": "json",
                                                 "posterior_response": [{"key": "token", "value": "$.token"}],
                                                 "ass_jsonpath": [
                                                     {"actual": "$.code", "expect": 0, "method": "p_is_equal_to"}]}],
            }],
        })

        self.assertTrue(preview["compatible"])
        self.assertEqual(preview["step_count"], 1)
        self.assertEqual(preview["steps"][0]["extractor_count"], 1)

    def test_case_parameter_groups_are_explicitly_incompatible_with_performance_mode(self):
        preview = PerfSourceCaseService._preview_payload({
            "api_case": {
                "parametrize": [{"name": "校准事件001", "parametrize": [{"key": "perf_event_id", "value": "1"}]}]},
        })
        self.assertFalse(preview["compatible"])
        self.assertIn("参数组", "；".join(preview["incompatible_reasons"]))
        self.assertNotIn("parameter_sets", preview)
        self.assertNotIn("parameter_strategy", {field.name for field in PerfScenario._meta.fields})
        self.assertNotIn("parameter_strategy", PerfScenarioWriteSerializer().fields)
        self.assertNotIn("parameter_strategy", PerfScenarioIR.model_fields)
        self.assertNotIn("parameter_sets", PerfScenarioIR.model_fields)

    def test_default_concurrency_load_is_immediately_editable(self):
        values = PerfLoadStageService.default_payload(PerfLoadTypeEnum.CONCURRENCY.value)
        self.assertEqual(values["name"], "基础负载")
        self.assertEqual(values["duration_seconds"], 60)
        self.assertEqual(values["target_users"], 10)
        self.assertEqual(values["user_wait_min_ms"], 0)

    def test_default_open_load_has_rate_and_vu_capacity(self):
        values = PerfLoadStageService.default_payload(PerfLoadTypeEnum.ARRIVAL_RATE.value)
        self.assertIsNone(values["target_users"])
        self.assertEqual(values["target_rate"], 10)
        self.assertEqual(values["rate_time_unit"], "second")
        self.assertEqual(values["preallocated_vus"], 10)
        self.assertEqual(values["max_vus"], 100)

    def test_fixed_iterations_profile_is_one_configuration(self):
        payload = {**PerfLoadStageService.default_payload(), "profile": "fixed_iterations",
                   "target_users": 20, "total_iterations": 10000, "duration_seconds": 300}
        normalized = PerfLoadStageService.normalize_payload(payload, executor_count=2)
        self.assertEqual(normalized["total_iterations"], 10000)
        self.assertEqual(normalized["duration_seconds"], 300)
        self.assertEqual(normalized["load_type"], "concurrency")
        self.assertEqual(len(PerfLoadStageService.build_stages(SimpleNamespace(
            load_type="concurrency", default_executor_count=2, load_name="定量", load_profile="fixed_iterations",
            duration_seconds=300, target_users=20, target_rate=None, rate_time_unit=None,
            preallocated_vus=None, max_vus=None, ramp_type="step", spawn_rate=None,
            user_wait_min_ms=0, user_wait_max_ms=0,
            **{key: normalized[key] for key in PerfLoadStageService.FIELD_NAMES},
        ))), 1)

    def test_staircase_profile_expands_in_order(self):
        payload = {**PerfLoadStageService.default_payload(), "profile": "staircase",
                   "target_users": 25, "step_users": 10, "step_interval_seconds": 15, "hold_seconds": 5}
        normalized = PerfLoadStageService.normalize_payload(payload, executor_count=2)
        scenario = SimpleNamespace(
            load_type="concurrency", default_executor_count=2, load_name="阶梯", load_profile="staircase",
            duration_seconds=normalized["duration_seconds"], target_users=25, target_rate=None,
            rate_time_unit=None, preallocated_vus=None, max_vus=None, ramp_type="step", spawn_rate=None,
            user_wait_min_ms=0, user_wait_max_ms=0,
            **{key: normalized[key] for key in PerfLoadStageService.FIELD_NAMES},
        )
        stages = PerfLoadStageService.build_stages(scenario)
        self.assertEqual([stage["target_users"] for stage in stages], [10, 20, 25, 25])
        self.assertEqual(sum(stage["duration_seconds"] for stage in stages), 50)

    def test_load_profile_rejects_oversubscription_across_nodes(self):
        payload = {**PerfLoadStageService.default_payload(), "profile": "fixed_iterations",
                   "target_users": 1, "total_iterations": 10}
        with self.assertRaises(PerfError):
            PerfLoadStageService.normalize_payload(payload, executor_count=2)

    def test_iteration_wait_is_validated_as_part_of_load_configuration(self):
        payload = {**PerfLoadStageService.default_payload(), "user_wait_min_ms": 100, "user_wait_max_ms": 250}
        normalized = PerfLoadStageService.normalize_payload(payload)
        self.assertEqual((normalized["user_wait_min_ms"], normalized["user_wait_max_ms"]), (100, 250))
        with self.assertRaises(PerfError):
            PerfLoadStageService.normalize_payload({**payload, "user_wait_max_ms": 50})

    def test_linear_spike_soak_and_rate_profiles_have_expected_duration(self):
        base = PerfLoadStageService.default_payload()
        linear = PerfLoadStageService.normalize_payload({**base, "profile": "linear_ramp",
                                                         "target_users": 30, "start_users": 2, "ramp_seconds": 40,
                                                         "hold_seconds": 20})
        spike = PerfLoadStageService.normalize_payload({**base, "profile": "spike",
                                                        "target_users": 30, "start_users": 2, "baseline_seconds": 10,
                                                        "ramp_seconds": 5, "hold_seconds": 10, "recovery_seconds": 5})
        soak = PerfLoadStageService.normalize_payload({**base, "profile": "soak", "duration_seconds": 3600})
        rate = PerfLoadStageService.normalize_payload({**PerfLoadStageService.default_payload("arrival_rate"),
                                                       "profile": "constant_arrival_rate", "target_rate": 120,
                                                       "rate_time_unit": "minute", "preallocated_vus": 4, "max_vus": 8},
                                                      executor_count=2)
        self.assertEqual((linear["duration_seconds"], spike["duration_seconds"], soak["duration_seconds"]),
                         (60, 30, 3600))
        self.assertEqual(rate["load_type"], "arrival_rate")
        self.assertEqual(rate["target_rate"], Decimal("120"))

    def test_default_performance_goal_is_one_configuration(self):
        values = PerfPerformanceGoalService.default_payload()
        self.assertEqual(values["template_key"], "recommended")
        self.assertEqual(values["p95_ms"], 500)
        self.assertEqual(values["max_error_rate"], 0.01)
        self.assertEqual(values["min_load_achievement_rate"], 0.95)

    def test_performance_goal_is_single_object_with_three_and_rules(self):
        scenario = PerfScenarioIR.model_validate({
            "scenario_id": 1,
            "scenario_version": 1,
            "name": "单目标场景",
            "project_product_id": 1,
            "module_id": 1,
            "engine": "k6",
            "source_case_id": 1,
            "source_case_release_id": 1,
            "source_case_revision_id": 1,
            "source_case_revision_checksum": "a" * 64,
            "source_case_version_label": "v1",
            "execution_mode": "sequential",
            "load_type": "concurrency",
            "user_wait_min_ms": 0,
            "user_wait_max_ms": 0,
            "steps": [{
                "step_key": "s1", "name": "请求", "sort": 0, "api_info_id": 1,
                "api_revision_id": 1, "api_revision_checksum": "x", "request": {},
            }],
            "stages": [{
                "stage_key": "stage-1", "name": "基础负载", "duration_seconds": 60,
                "target_users": 10,
            }],
            "performance_goal": {
                "template_key": "custom", "p95_ms": 800,
                "max_error_rate": 0.02, "min_load_achievement_rate": 0.9,
            },
        })

        rules = PerfPerformanceGoalService.to_result_rules(scenario.performance_goal.model_dump())

        self.assertEqual(len(rules), 3)
        self.assertEqual([item["operator"] for item in rules], ["<=", "<=", ">="])
        with self.assertRaises(ValidationError):
            PerfScenarioIR.model_validate(
                {**scenario.model_dump(), "performance_goal": [scenario.performance_goal.model_dump()]})

    def test_configuration_replacement_rejects_missing_lists(self):
        with self.assertRaises(PerfError) as context:
            PerfScenarioConfigurationService.validate_replacement(
                {"load_config": {}},
            )
        self.assertIn("来源API自动化 Case、性能目标", context.exception.msg)

    def test_configuration_replacement_protects_existing_components(self):
        payload = {"source_case_release_id": 1, "load_config": {}, "performance_goal": {}}
        with self.assertRaises(PerfError) as context:
            PerfScenarioConfigurationService.validate_replacement(
                payload,
            )
        self.assertIn("负载配置", context.exception.msg)

    def test_configuration_replacement_allows_new_draft_and_explicit_clear(self):
        payload = {"source_case_release_id": 1, "load_config": {"duration_seconds": 60}, "performance_goal": {}}
        PerfScenarioConfigurationService.validate_replacement(payload)

    def test_empty_scenario_components_have_actionable_error(self):
        with self.assertRaises(PerfError) as context:
            ensure_required_scenario_components([], [])
        self.assertEqual(
            context.exception.msg,
            "性能场景配置无效：来源 Case 至少需要 1 个可执行的 HTTP 步骤；请配置负载",
        )

    def test_executor_policy_requires_specified_fingerprints(self):
        with self.assertRaises(ValidationError):
            PerfExecutorPolicy.model_validate({"mode": "specified", "specified_executor_fingerprints": []})

    def test_scenario_requires_load_target_for_every_stage(self):
        data = {
            "schema_version": 1, "scenario_id": 1, "scenario_version": 1, "name": "容量场景",
            "project_product_id": 1, "module_id": 1, "engine": "k6",
            "execution_mode": "sequential", "load_type": "concurrency",
            "user_wait_min_ms": 0, "user_wait_max_ms": 0,
            "steps": [{
                "step_key": "s1", "name": "请求", "sort": 0, "api_info_id": 1,
                "api_revision_id": 1, "api_revision_checksum": "x", "request": {},
            }],
            "stages": [{"stage_key": "stage-1", "name": "升压", "duration_seconds": 10}],
        }
        with self.assertRaises(ValidationError):
            PerfScenarioIR.model_validate(data)

    def test_scenario_rejects_non_k6_engine(self):
        data = {
            "schema_version": 1, "scenario_id": 1, "scenario_version": 1, "name": "容量场景",
            "project_product_id": 1, "module_id": 1, "engine": "locust",
            "execution_mode": "sequential", "load_type": "concurrency",
            "user_wait_min_ms": 0, "user_wait_max_ms": 0,
            "steps": [{
                "step_key": "s1", "name": "请求", "sort": 0, "api_info_id": 1,
                "api_revision_id": 1, "api_revision_checksum": "x", "request": {},
            }],
            "stages": [{"stage_key": "stage-1", "name": "稳态", "duration_seconds": 10, "target_users": 10}],
        }
        with self.assertRaises(ValidationError):
            PerfScenarioIR.model_validate(data)

    def test_metric_batch_requires_monotonic_sequences(self):
        point = {
            "window_start": datetime.now(timezone.utc), "window_seconds": 1,
            "scope_type": "global", "scope_key": "__all__",
        }
        with self.assertRaises(ValidationError):
            PerfMetricBatch.model_validate({
                "schema_version": 1, "run_id": 1, "run_node_id": 2,
                "points": [{**point, "sequence": 2}, {**point, "sequence": 1}],
            })

    def test_secret_redaction_is_recursive_and_hash_is_stable(self):
        value = {"headers": {"Authorization": "Bearer secret"}, "nested": [{"token": "abc", "safe": 1}]}
        redacted = redact_secrets(value)
        self.assertEqual(redacted["headers"]["Authorization"], "***")
        self.assertEqual(redacted["nested"][0]["token"], "***")
        self.assertEqual(snapshot_hash(redacted),
                         snapshot_hash({"nested": redacted["nested"], "headers": redacted["headers"]}))

    def test_cursor_is_opaque_and_round_trips(self):
        cursor = PerfMetricService.encode_cursor(123456)
        self.assertNotIn("123456", cursor)
        self.assertEqual(PerfMetricService.decode_cursor(cursor), 123456)

    def test_secret_paths_are_redacted_and_ciphertext_is_reversible(self):
        redacted, values = extract_secrets({"headers": {"Authorization": "Bearer value"}}, "steps.0.request")
        self.assertEqual(redacted["headers"]["Authorization"], "***")
        self.assertEqual(values["steps.0.request.headers.Authorization"], "Bearer value")
        encrypted = PerfSecretService._cipher().encrypt(b'{"secret":true}')
        self.assertNotIn(b"secret", encrypted)
        self.assertEqual(PerfSecretService._cipher().decrypt(encrypted), b'{"secret":true}')


class PerfModelContractTests(SimpleTestCase):
    def test_scenario_engine_defaults_to_k6_and_rejects_unsupported_values(self):
        field = PerfScenario._meta.get_field("engine")
        self.assertEqual(field.default, "k6")
        self.assertEqual(list(field.choices), [("k6", "k6")])
        self.assertTrue(PerfScenarioWriteSerializer(data={"engine": "k6", "target_users": 10}, partial=True).is_valid())
        self.assertFalse(
            PerfScenarioWriteSerializer(data={"engine": "locust", "target_users": 10}, partial=True).is_valid())

    def test_core_tables_and_metric_uniqueness_exist(self):
        self.assertEqual(PerfScenario._meta.db_table, "perf_scenario")
        self.assertEqual(PerfRun._meta.db_table, "perf_run")
        self.assertFalse({"plan", "parent_run", "run_type", "plan_snapshot", "plan_item_sort"} & {
            field.name for field in PerfRun._meta.fields
        })
        names = {constraint.name for constraint in PerfMetricInterval._meta.constraints}
        self.assertIn("uniq_perf_metric_batch_scope", names)

    def test_run_terminal_states_are_explicit(self):
        self.assertIn("completed", PerfRunStatusEnum.terminal_values())
        self.assertNotIn("running", PerfRunStatusEnum.terminal_values())

    def test_detail_routes_bind_callable_retrieve_actions(self):
        detail_routes = {"scenario/<int:pk>", "run/<int:pk>"}
        self.assertFalse(any(str(pattern.pattern).startswith("plan") for pattern in urlpatterns))
        matched = 0
        for pattern in urlpatterns:
            if str(pattern.pattern) not in detail_routes:
                continue
            matched += 1
            action = pattern.callback.actions["get"]
            self.assertEqual(action, "retrieve")
            self.assertTrue(callable(getattr(pattern.callback.cls(), action)))
        self.assertEqual(matched, len(detail_routes))
