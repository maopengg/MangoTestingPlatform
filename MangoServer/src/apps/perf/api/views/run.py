import json
import posixpath

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.perf.api.serializers.run import PerfRunListSerializer
from src.apps.perf.api.views.common import ensure_perf_data_scope
from src.apps.perf.api.views.scenario import request_user
from src.apps.perf.exceptions import (
    PERF_PERF_NOT_FOUND,
    PERF_PERF_INVALID,
    PERF_REQUEST_RECORD_NODE_EXECUTION_DOWNLOAD_INVALID,
    PerfError,
)
from src.apps.perf.formatters import format_perf_datetime, format_perf_row_datetimes
from src.apps.perf.models import (
    PerfBaseline, PerfRequestSummary, PerfRun, PerfRunError, PerfRunEvent, PerfRunNode,
)
from src.apps.perf.services import PerfExecutionService, PerfFinalizeService, PerfMetricService, PerfRealtimeService
from src.apps.perf.services.reporting.baseline import PerfBaselineService
from src.apps.test_center.services.storage.execution_artifact import ExecutionArtifactService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0082


class PerfRunCRUD(ModelCRUD):
    http_method_names = ['get', 'head', 'options']
    model = PerfRun
    queryset = PerfRun.objects.all()
    serializer_class = PerfRunListSerializer
    serializer = PerfRunListSerializer
    page_permission_key = "perf.run"


class PerfRunViews(ViewSet):

    @staticmethod
    def _get(request, pk):
        run = PerfRun.objects.select_related("scenario", "project_product", "module", "created_by").filter(
            id=pk).first()
        if not run:
            raise PerfError(PERF_PERF_NOT_FOUND)
        ensure_perf_data_scope(request, run.project_product_id)
        return run

    @error_response("system")
    def retrieve(self, request: Request, pk=None):
        """获取性能测试运行记录详情"""
        run = self._get(request, pk)
        data = PerfRunListSerializer(run).data
        data["summary"] = run.summary
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @error_response("system")
    def overview(self, request: Request, pk=None):
        """获取性能测试运行记录概览"""
        run = self._get(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, {
            "id": run.id, "name": run.name, "status": run.status, "verdict": run.verdict,
            "scenario_id": run.scenario_id,
            "project_product": {"id": run.project_product_id, "name": run.project_product.name},
            "module": {"id": run.module_id, "name": run.module.name,
                       "full_path": run.module.get_full_path()} if run.module_id else None,
            "creator_name": (run.created_by.name or run.created_by.username) if run.created_by else "",
            "summary": run.summary, "requested_node_count": run.requested_node_count,
            "actual_node_count": run.actual_node_count, "peak_target_users": run.peak_target_users,
            "duration_seconds": run.duration_seconds,
            "started_at": format_perf_datetime(run.started_at),
            "finished_at": format_perf_datetime(run.finished_at),
            "revision": run.revision, "test_env": run.test_env, "test_env_title": run.test_env_title,
            "engine": run.engine, "engine_version": run.engine_version, "remark": run.remark,
            "capture": (run.execution_policy or {}).get("capture", {"request": False, "response": False}),
            "error_code": run.error_code, "error_message": run.error_message,
        })

    @error_response("system")
    def metrics(self, request: Request, pk=None):
        """获取性能测试运行记录指标"""
        self._get(request, pk)
        data = PerfMetricService.query(
            run_id=int(pk), cursor=request.query_params.get("cursor"),
            max_points=int(request.query_params.get("max_points", 500)),
            scope_type=request.query_params.get("scope_type"), scope_key=request.query_params.get("scope_key"),
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    def _rows(self, model, pk, fields):
        return [format_perf_row_datetimes(row) for row in model.objects.filter(run_id=pk).values(*fields)]

    @error_response("system")
    def requests(self, request, pk=None):
        """获取性能测试请求统计"""
        self._get(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, self._rows(PerfRequestSummary, pk, [field.name for field in
                                                                                           PerfRequestSummary._meta.fields]))

    @error_response("system")
    def stages(self, request, pk=None):
        """获取性能测试阶段统计"""
        run = self._get(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, (run.load_summary or {}).get("items", []))

    @error_response("system")
    def nodes(self, request, pk=None):
        """获取性能测试节点信息"""
        self._get(request, pk)
        fields = [field.name for field in PerfRunNode._meta.fields if
                  field.name not in {"allocated_load", "result_summary", "resource_summary"}]
        rows = self._rows(PerfRunNode, pk, fields)
        captures = {
            node.id: {key: value for key, value in (node.result_summary or {}).get("capture", {}).items() if
                      key != "path"}
            for node in PerfRunNode.objects.filter(run_id=pk).only("id", "result_summary")
        }
        for row in rows:
            row["capture"] = captures.get(row["id"], {})
        return ResponseData.success(RESPONSE_MSG_0001, rows)

    @error_response("system")
    def capture_download(self, request, pk=None, node_id=None):
        """下载性能测试采集文件"""
        self._get(request, pk)
        node = PerfRunNode.objects.filter(id=node_id, run_id=pk).only("result_summary").first()
        capture = (node.result_summary or {}).get("capture", {}) if node else {}
        if capture.get("status") != "uploaded" or not capture.get("path"):
            raise PerfError(PERF_REQUEST_RECORD_NODE_EXECUTION_DOWNLOAD_INVALID)
        try:
            path = ExecutionArtifactService.normalize_path(capture["path"])
        except (TypeError, ValueError) as error:
            raise PerfError(PERF_REQUEST_RECORD_NODE_EXECUTION_DOWNLOAD_INVALID) from error
        expected = f"perf-run-{pk}-node-{node_id}.csv"
        if "://" in path or posixpath.basename(
                path) != expected or f"/{ExecutionArtifactService.PERF_CAPTURE_DIRECTORY}/" not in f"/{path}":
            raise PerfError(PERF_REQUEST_RECORD_NODE_EXECUTION_DOWNLOAD_INVALID)
        return ResponseData.success(RESPONSE_MSG_0001,
                                    {"url": ExecutionArtifactService.public_url(path), "name": expected})

    @error_response("system")
    def errors(self, request, pk=None):
        """获取性能测试运行记录错误信息"""
        self._get(request, pk)
        rows = list(PerfRunError.objects.filter(run_id=pk).order_by("-count"))
        data = [{
            "id": row.id, "step_key": row.step_key, "fingerprint": row.fingerprint,
            "error_type": row.error_type, "error_code": row.error_code, "message_template": row.message_template,
            "count": row.count,
            "first_seen_at": format_perf_datetime(row.first_seen_at),
            "last_seen_at": format_perf_datetime(row.last_seen_at),
            "node_count": row.node_count,
            "samples": row.samples or [],
        } for row in rows]
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @error_response("system")
    def thresholds(self, request, pk=None):
        """获取性能测试阈值判定"""
        run = self._get(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, (run.performance_goal_result or {}).get("items", []))

    @error_response("system")
    def validity(self, request, pk=None):
        """获取性能测试结果有效性信息"""
        run = self._get(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, run.validity_results or [])

    @error_response("system")
    def events(self, request, pk=None):
        """获取性能测试运行事件"""
        self._get(request, pk)
        after_id = int(request.query_params.get("after_id", 0))
        run_ids = [int(pk)]
        rows = [format_perf_row_datetimes(row) for row in
                PerfRunEvent.objects.filter(run_id__in=run_ids, id__gt=after_id).order_by("id").values()[:1000]]
        return ResponseData.success(RESPONSE_MSG_0001, rows)

    @error_response("system")
    def snapshot(self, request, pk=None):
        """获取性能测试运行配置快照"""
        run = self._get(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, {
            "snapshot_hash": run.snapshot_hash,
            "scenario_snapshot": run.scenario_snapshot,
        })

    @error_response("system")
    def export(self, request, pk=None):
        """导出性能测试运行报告"""
        run = self._get(request, pk)
        report = {
            "schema_version": 1,
            "run": PerfRunListSerializer(run).data,
            "summary": run.summary,
            "scenario_snapshot": run.scenario_snapshot,
            "requests": self._rows(PerfRequestSummary, pk, [field.name for field in PerfRequestSummary._meta.fields]),
            "stages": (run.load_summary or {}).get("items", []),
            "nodes": self._rows(PerfRunNode, pk, [
                field.name for field in PerfRunNode._meta.fields
                if field.name not in {"allocated_load", "result_summary", "resource_summary"}
            ]),
            "thresholds": (run.performance_goal_result or {}).get("items", []),
            "validity": run.validity_results or [],
            "capacity": run.capacity_result or {},
            "errors": [format_perf_row_datetimes(row) for row in PerfRunError.objects.filter(run_id=pk).values(
                "step_key", "error_type", "error_code", "message_template", "count",
                "node_count", "first_seen_at", "last_seen_at",
            )],
            "events": [format_perf_row_datetimes(row) for row in
                       PerfRunEvent.objects.filter(run_id=pk).order_by("id").values()],
        }
        response = HttpResponse(
            json.dumps(report, ensure_ascii=False, cls=DjangoJSONEncoder, separators=(",", ":")),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="perf-run-{run.id}.json"'
        return response

    @error_response("system")
    def rerun(self, request, pk=None):
        """重新执行性能测试运行配置"""
        source = self._get(request, pk)
        if source.test_env == 2 and request.data.get("production_load_confirmed") is not True:
            raise PerfError(PERF_PERF_INVALID)
        if not source.scenario_id:
            raise PerfError(PERF_PERF_NOT_FOUND)
        selected = request.data.get("selected_executor_fingerprints") or []
        with transaction.atomic():
            run = PerfExecutionService.create_direct_run(
                scenario_id=source.scenario_id, user=request_user(request), test_env=source.test_env,
                selected_executor_fingerprints=selected,
                remark=f"按运行 #{source.id} 的当前场景配置重新执行",
                capture_request=bool((source.execution_policy or {}).get("capture", {}).get("request")),
                capture_response=bool((source.execution_policy or {}).get("capture", {}).get("response")),
            )
            PerfExecutionService.dispatch_run(run.id)
        run.refresh_from_db()
        return ResponseData.success(RESPONSE_MSG_0002, {"run_id": run.id, "status": run.status})

    @error_response("system")
    def stop(self, request, pk=None):
        """停止性能测试运行记录"""
        self._get(request, pk)
        run = PerfExecutionService.request_stop(int(pk), cancel=False)
        return ResponseData.success(RESPONSE_MSG_0082, {"id": run.id, "status": run.status})

    @error_response("system")
    def cancel(self, request, pk=None):
        """取消性能测试运行记录"""
        self._get(request, pk)
        run = PerfExecutionService.request_stop(int(pk), cancel=True)
        return ResponseData.success(RESPONSE_MSG_0082, {"id": run.id, "status": run.status})

    @error_response("system")
    def finalize(self, request, pk=None):
        """结算性能测试运行结果"""
        self._get(request, pk)
        run = PerfFinalizeService.finalize(int(pk))
        return ResponseData.success(RESPONSE_MSG_0082, {"id": run.id, "status": run.status, "verdict": run.verdict})

    @error_response("system")
    def set_baseline(self, request, pk=None):
        """设置性能测试对比基线"""
        run = self._get(request, pk)
        baseline = PerfBaselineService.set_baseline(
            run, name=request.data.get("name"), created_by=request_user(request),
        )
        return ResponseData.success(RESPONSE_MSG_0002, {"id": baseline.id})

    @error_response("system")
    def comparison(self, request, pk=None):
        """获取性能测试基线对比结果"""
        run = self._get(request, pk)
        baseline_run_id = request.query_params.get("baseline_run_id")
        if baseline_run_id:
            baseline_run = PerfRun.objects.filter(id=baseline_run_id, scenario_id=run.scenario_id).first()
        else:
            baseline = PerfBaseline.objects.select_related("run").filter(
                scenario_id=run.scenario_id, environment_key=str(run.test_env), engine=run.engine, active=True,
            ).first()
            baseline_run = baseline.run if baseline else None
        if not baseline_run:
            return ResponseData.success(RESPONSE_MSG_0001, {"available": False, "metrics": []})
        ensure_perf_data_scope(request, baseline_run.project_product_id)
        metrics = []
        for key in ("request_count", "failure_count", "avg_ms", "p95_ms", "p99_ms", "rps"):
            current = float(run.summary.get(key) or 0)
            previous = float(baseline_run.summary.get(key) or 0)
            metrics.append({
                "metric": key, "current": current, "baseline": previous, "delta": current - previous,
                "delta_percent": ((current - previous) / previous * 100) if previous else None,
            })
        return ResponseData.success(RESPONSE_MSG_0001, {
            "available": True, "baseline_run_id": baseline_run.id,
            "compatible": run.engine == baseline_run.engine and run.test_env == baseline_run.test_env,
            "same_snapshot": run.snapshot_hash == baseline_run.snapshot_hash,
            "metrics": metrics,
        })

    @error_response("system")
    def subscription(self, request, pk=None):
        """订阅或取消订阅性能测试实时更新"""
        self._get(request, pk)
        user = request_user(request)
        if request.method == "DELETE":
            PerfRealtimeService.unsubscribe("run", int(pk), user.id)
        else:
            PerfRealtimeService.subscribe("run", int(pk), user.id)
        return ResponseData.success(RESPONSE_MSG_0082, {"ttl_seconds": PerfRealtimeService.TTL_SECONDS})
