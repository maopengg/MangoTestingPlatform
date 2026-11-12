import json

from django.db import transaction
from mangotools.perf.k6_script import K6_SCRIPT_SOURCE
from pydantic import ValidationError
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.perf.api.serializers.scenario import (
    PerfScenarioListSerializer,
    PerfScenarioWriteSerializer,
)
from src.apps.perf.api.views.common import ensure_perf_data_scope
from src.apps.perf.exceptions import (
    PERF_SCENARIO_CONFIG_PERF_INVALID,
    PERF_SCENARIO_DELETE_PERF_NOT_ALLOWED,
    PERF_PERF_INVALID,
    PerfError,
)
from src.apps.perf.formatters import format_perf_row_datetimes
from src.apps.perf.models import PerfScenario
from src.apps.perf.schemas.execution import PerfExecutorPolicy, PerfPerformanceGoalIR
from src.apps.perf.services import (
    PerfCapacityService,
    PerfExecutionService,
    PerfScenarioCompiler,
    PerfScenarioConfigurationService,
    PerfPerformanceGoalService,
    PerfLoadStageService,
    PerfSourceCaseService,
)
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002


def request_user(request: Request):
    """获取当前请求用户"""
    wrapper = getattr(request, "user", None)
    user = getattr(wrapper, "user_obj", None)
    if user is not None:
        return user
    return None


class PerfScenarioCRUD(ModelCRUD):
    model = PerfScenario
    queryset = PerfScenario.objects.all()
    serializer_class = PerfScenarioListSerializer
    serializer = PerfScenarioWriteSerializer
    page_permission_key = "perf.scenario"

    @error_response("system")
    def delete(self, request):
        """删除性能测试场景"""
        scenario_id = request.query_params.get("id")
        if scenario_id and PerfScenario.objects.filter(id=scenario_id, runs__isnull=False).exists():
            raise PerfError(PERF_SCENARIO_DELETE_PERF_NOT_ALLOWED)
        return super().delete(request)


class PerfScenarioViews(ViewSet):

    @error_response("system")
    def executors(self, request: Request):
        """获取性能场景可用执行器"""
        rows = PerfCapacityService.list_available_executors()
        return ResponseData.success(RESPONSE_MSG_0001, [format_perf_row_datetimes(row) for row in rows])

    @error_response("system")
    def retrieve(self, request: Request, pk=None):
        """获取性能测试场景详情"""
        scenario = PerfScenario.objects.select_related("project_product", "module", "owner", "source_api_case",
                                                       "source_case_release", "source_case_revision").filter(
            id=pk).first()
        if not scenario:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
        ensure_perf_data_scope(request, scenario.project_product_id)
        data = PerfScenarioWriteSerializer(scenario).data
        data.update({
            "module_full_path": scenario.module.get_full_path(),
            "source_api_case_id": scenario.source_api_case_id,
            "source_case_release_id": scenario.source_case_release_id,
            "source_case_revision_id": scenario.source_case_revision_id,
            "load_config": PerfLoadStageService.serialize(scenario),
            "source_case": PerfSourceCaseService.serialize_release(
                scenario.source_case_release) if scenario.source_case_release_id else None,
            "performance_goal": PerfPerformanceGoalService.serialize(scenario),
        })
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @error_response("system")
    def source_api_cases(self, request: Request, pk=None):
        """获取性能场景可选 API 用例"""
        scenario = PerfScenario.objects.only("id", "project_product_id").filter(id=pk).first()
        if not scenario:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
        ensure_perf_data_scope(request, scenario.project_product_id)
        return ResponseData.success(RESPONSE_MSG_0001, PerfSourceCaseService.list_options(scenario))

    @error_response("system")
    def configuration(self, request: Request, pk=None):
        """获取或保存性能测试场景配置"""
        from django.db import transaction
        with transaction.atomic():
            scenario = PerfScenario.objects.select_for_update().filter(id=pk).first()
            if not scenario:
                raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
            ensure_perf_data_scope(request, scenario.project_product_id)
            if int(request.data.get("version", 0)) != scenario.version:
                from src.apps.perf.exceptions import PERF_VERSION_CONFIG_PERF_INVALID
                raise PerfError(PERF_VERSION_CONFIG_PERF_INVALID)
            PerfScenarioConfigurationService.validate_replacement(request.data)
            release = PerfSourceCaseService.resolve_release(scenario, int(request.data["source_case_release_id"]))
            if release is None:
                raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("来源 Case 未发布、已失效或不属于当前产品",))
            preview = PerfSourceCaseService.serialize_release(release)
            if not preview["compatible"]:
                raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID,
                                value=("来源 Case 暂不兼容性能模式：" + "；".join(preview["incompatible_reasons"]),))
            base = dict(request.data.get("base") or {})
            base.update({
                "source_api_case": release.api_case_id,
                "source_case_release": release.id,
                "source_case_revision": release.revision_id,
                "execution_mode": "sequential",
            })
            load_payload = dict(request.data["load_config"])
            load_payload.setdefault("user_wait_min_ms", base.get("user_wait_min_ms", scenario.user_wait_min_ms))
            load_payload.setdefault("user_wait_max_ms", base.get("user_wait_max_ms", scenario.user_wait_max_ms))
            base.update(PerfLoadStageService.normalize_payload(
                load_payload, int(base.get("default_executor_count") or scenario.default_executor_count)
            ))
            serializer = PerfScenarioWriteSerializer(scenario, data=base, partial=True)
            serializer.is_valid(raise_exception=True)
            scenario = serializer.save(update_user=request_user(request))
            try:
                goal = PerfPerformanceGoalIR.model_validate(request.data.get("performance_goal"))
            except ValidationError as exc:
                message = "; ".join(error["msg"] for error in exc.errors()[:5])
                raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=(f"性能目标配置无效：{message}",)) from exc
            scenario.goal_template_key = goal.template_key
            scenario.goal_p95_ms = goal.p95_ms
            scenario.goal_max_error_rate = goal.max_error_rate
            scenario.goal_min_load_achievement_rate = goal.min_load_achievement_rate
            scenario.save(update_fields=["goal_template_key", "goal_p95_ms", "goal_max_error_rate",
                                         "goal_min_load_achievement_rate", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0002, {"id": scenario.id, "version": scenario.version})

    @error_response("system")
    def validate(self, request: Request, pk=None):
        """校验性能测试场景配置"""
        scenario = PerfScenario.objects.filter(id=pk).first()
        if not scenario:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
        ensure_perf_data_scope(request, scenario.project_product_id)
        snapshot, digest = PerfScenarioCompiler.compile(scenario)
        return ResponseData.success(RESPONSE_MSG_0001, {
            "valid": True, "snapshot_hash": digest, "step_count": len(snapshot["steps"]),
            "duration_seconds": scenario.duration_seconds,
        })

    @error_response("system")
    def script_preview(self, request: Request, pk=None):
        """预览性能测试编译脚本"""
        scenario = PerfScenario.objects.select_related("source_case_release", "source_case_revision").filter(
            id=pk).first()
        if not scenario:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
        ensure_perf_data_scope(request, scenario.project_product_id)
        snapshot, digest = PerfScenarioCompiler.compile(scenario)
        return ResponseData.success(RESPONSE_MSG_0001, {
            "scenario_version": scenario.version,
            "snapshot_hash": digest,
            "script": K6_SCRIPT_SOURCE,
            "snapshot": json.dumps(snapshot, ensure_ascii=False, indent=2),
        })

    @error_response("system")
    def execute(self, request: Request, pk=None):
        """执行性能测试场景"""
        scenario = PerfScenario.objects.filter(id=pk).only("project_product_id").first()
        if not scenario:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
        ensure_perf_data_scope(request, scenario.project_product_id)
        test_env = int(request.data.get("test_env", 0))
        if test_env == 2 and request.data.get("production_load_confirmed") is not True:
            raise PerfError(PERF_PERF_INVALID)
        selected = request.data.get("selected_executor_fingerprints") or []
        with transaction.atomic():
            run = PerfExecutionService.create_direct_run(
                scenario_id=int(pk), user=request_user(request), test_env=test_env,
                selected_executor_fingerprints=selected,
                remark=str(request.data.get("remark", ""))[:512],
                capture_request=request.data.get("capture_request") is True,
                capture_response=request.data.get("capture_response") is True,
            )
            PerfExecutionService.dispatch_run(run.id)
        run.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0002, {"run_id": run.id, "status": run.status})

    @error_response("system")
    def preflight(self, request: Request, pk=None):
        """检查性能测试执行前的容量与条件"""
        scenario = PerfScenario.objects.filter(id=pk, status=1).first()
        if not scenario:
            raise PerfError(PERF_SCENARIO_CONFIG_PERF_INVALID, value=("场景不存在",))
        ensure_perf_data_scope(request, scenario.project_product_id)
        snapshot, _ = PerfScenarioCompiler.compile(scenario)
        snapshot = PerfExecutionService._bind_environment(
            snapshot, test_env=int(request.data["test_env"]), project_product_id=scenario.project_product_id,
        )
        selected = request.data.get("selected_executor_fingerprints") or []
        policy = PerfExecutorPolicy(
            mode="specified" if selected else "auto",
            specified_executor_fingerprints=selected,
            min_ready_nodes=scenario.min_ready_nodes or scenario.default_executor_count,
            node_failure_policy=scenario.node_failure_policy,
        ).model_dump(mode="json")
        data = PerfCapacityService.estimate_snapshot(
            engine=snapshot["engine"], snapshot=snapshot,
            requested_node_count=scenario.default_executor_count, policy=policy,
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)
