import json
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from src.apps.perf.enums import (
    PerfRunNodeStatusEnum, PerfRunStatusEnum, PerfRunVerdictEnum,
    PerfThresholdSeverityEnum, PerfValidityStatusEnum,
)
from src.apps.perf.exceptions import (
    PERF_STATUS_EXECUTION_NOT_ALLOWED,
    PERF_PERF_NOT_FOUND,
    PerfError,
)
from src.apps.perf.models import (
    PerfMetricInterval, PerfRequestSummary, PerfRun, PerfRunEvent,
)
from src.apps.perf.services.capacity.capacity import PerfCapacityService
from src.apps.perf.services.scenario.performance_goal import PerfPerformanceGoalService


def _percentile(buckets: dict[int, int], percentile: float) -> Decimal:
    total = sum(buckets.values())
    if not total:
        return Decimal("0")
    target = max(1, int(total * percentile + 0.999999))
    cursor = 0
    for value, count in sorted(buckets.items()):
        cursor += count
        if cursor >= target:
            return Decimal(value)
    return Decimal(max(buckets))


def _merge_histogram(target: dict[int, int], value: str):
    if not value:
        return
    try:
        items = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return
    for key, count in items.items():
        target[int(key)] += int(count)


def _json_number(value, default=0):
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    return value


class PerfFinalizeService:
    ALGORITHM_VERSION = 1

    @staticmethod
    def _final_status(success_nodes: int, failed_nodes: int) -> str:
        if failed_nodes and not success_nodes:
            return PerfRunStatusEnum.FAILED.value
        if failed_nodes:
            return PerfRunStatusEnum.PARTIAL.value
        return PerfRunStatusEnum.COMPLETED.value

    @classmethod
    @transaction.atomic
    def finalize(cls, run_id: int) -> PerfRun:
        run = PerfRun.objects.select_for_update().filter(id=run_id).first()
        if not run:
            raise PerfError(PERF_PERF_NOT_FOUND)
        if run.status in PerfRunStatusEnum.terminal_values():
            return run
        if run.nodes.exclude(status__in=PerfRunNodeStatusEnum.terminal_values()).exists():
            raise PerfError(PERF_STATUS_EXECUTION_NOT_ALLOWED)
        run.status = PerfRunStatusEnum.AGGREGATING.value
        run.save(update_fields=["status", "update_time"])
        cls._aggregate_requests(run)
        run.load_summary = cls._aggregate_stages(run)
        valid = cls._evaluate_validity(run)
        critical_failed = cls._evaluate_performance_goal(run)
        certification = cls._certify_capacity(run, valid)
        success_nodes = run.nodes.filter(status=PerfRunNodeStatusEnum.SUCCESS.value).count()
        failed_nodes = run.nodes.exclude(status=PerfRunNodeStatusEnum.SUCCESS.value).count()
        run.status = cls._final_status(success_nodes, failed_nodes)
        run.verdict = (
            PerfRunVerdictEnum.INVALID.value if not valid
            else PerfRunVerdictEnum.FAILED.value if critical_failed
            else PerfRunVerdictEnum.PASSED.value
        )
        global_summary = PerfRequestSummary.objects.filter(run=run, step_key="").values().first() or {}
        interval_totals = PerfMetricInterval.objects.filter(run=run, scope_type="global").aggregate(
            iteration_count=Sum("iteration_count"),
            dropped_count=Sum("dropped_count"),
            connection_count=Sum("connection_count"),
            connect_error_count=Sum("connect_error_count"),
        )
        peak_cpu_percent = 0
        peak_memory_bytes = 0
        peak_event_loop_lag_ms = None
        memory_by_window = defaultdict(int)
        timing_weighted_sums = defaultdict(float)
        timing_weights = defaultdict(int)
        for window_start, generator_metrics, timing_breakdown, request_count in PerfMetricInterval.objects.filter(
                run=run, scope_type="global").values_list(
            "window_start", "generator_metrics", "timing_breakdown", "request_count",
        ).iterator(chunk_size=2000):
            metrics = generator_metrics or {}
            peak_cpu_percent = max(peak_cpu_percent, float(metrics.get("cpu_percent") or 0))
            memory_by_window[window_start.isoformat()] += int(metrics.get("memory_bytes") or 0)
            if metrics.get("event_loop_lag_ms") is not None:
                peak_event_loop_lag_ms = max(
                    peak_event_loop_lag_ms or 0, float(metrics["event_loop_lag_ms"]),
                )
            for field, value in (timing_breakdown or {}).items():
                if value is not None and request_count:
                    timing_weighted_sums[field] += float(value) * request_count
                    timing_weights[field] += request_count
        peak_memory_bytes = max(memory_by_window.values(), default=0)
        timing_summary = {
            field: timing_weighted_sums[field] / weight
            for field, weight in timing_weights.items()
            if weight
        }
        run.summary = {
            "schema_version": 1,
            "algorithm_version": cls.ALGORITHM_VERSION,
            "request_count": int(global_summary.get("request_count") or 0),
            "failure_count": int(global_summary.get("failure_count") or 0),
            "avg_ms": _json_number(global_summary.get("avg_ms")),
            "min_ms": _json_number(global_summary.get("min_ms")),
            "max_ms": _json_number(global_summary.get("max_ms")),
            "p50_ms": _json_number(global_summary.get("p50_ms")),
            "p90_ms": _json_number(global_summary.get("p90_ms")),
            "p95_ms": _json_number(global_summary.get("p95_ms")),
            "p99_ms": _json_number(global_summary.get("p99_ms")),
            "rps": _json_number(global_summary.get("rps")),
            "max_rps": _json_number(global_summary.get("max_rps")),
            "bytes_sent": int(global_summary.get("bytes_sent") or 0),
            "bytes_received": int(global_summary.get("bytes_received") or 0),
            "iteration_count": int(interval_totals.get("iteration_count") or 0),
            "dropped_count": int(interval_totals.get("dropped_count") or 0),
            "connection_count": int(interval_totals.get("connection_count") or 0),
            "connect_error_count": int(interval_totals.get("connect_error_count") or 0),
            "timing_breakdown": timing_summary,
            "peak_generator_cpu_percent": peak_cpu_percent,
            "peak_generator_memory_bytes": peak_memory_bytes,
            "peak_event_loop_lag_ms": peak_event_loop_lag_ms,
            "failed_node_count": failed_nodes,
            "capacity_certified": certification["valid"],
            "actual_peak_concurrency": certification["actual_peak_concurrency"],
            "actual_peak_rps": certification["actual_peak_rps"],
        }
        run.finished_at = run.finished_at or timezone.now()
        run.revision += 1
        run.save(update_fields=["status", "verdict", "summary", "load_summary", "validity_results",
                                "performance_goal_result", "capacity_result", "finished_at", "revision", "update_time"])
        PerfCapacityService.release(run.id)
        PerfRunEvent.objects.create(run=run, event_type="aggregation_completed", message="性能结果汇总完成",
                                    detail={"verdict": run.verdict}, occurred_at=timezone.now())
        from src.apps.perf.services.reporting.realtime import PerfRealtimeService
        transaction.on_commit(lambda: PerfRealtimeService.notify_run(run))
        return run

    @classmethod
    def _aggregate_requests(cls, run: PerfRun):
        PerfRequestSummary.objects.filter(run=run).delete()
        groups = defaultdict(lambda: {"count": 0, "failure": 0, "sum": 0, "min": None, "max": None,
                                      "sent": 0, "received": 0, "hist": defaultdict(int),
                                      "windows": defaultdict(Decimal)})
        for row in PerfMetricInterval.objects.filter(run=run, scope_type__in=["global", "request"]).iterator(
                chunk_size=2000):
            key = "" if row.scope_type == "global" else row.scope_key
            item = groups[key]
            item["count"] += row.request_count
            item["failure"] += row.failure_count
            item["sum"] += row.response_time_sum_ms
            item["sent"] += row.bytes_sent
            item["received"] += row.bytes_received
            item["windows"][row.window_start.isoformat()] += Decimal(row.request_count) / Decimal(
                max(1, row.window_seconds))
            if row.min_response_time_ms is not None:
                item["min"] = row.min_response_time_ms if item["min"] is None else min(item["min"],
                                                                                       row.min_response_time_ms)
            if row.max_response_time_ms is not None:
                item["max"] = row.max_response_time_ms if item["max"] is None else max(item["max"],
                                                                                       row.max_response_time_ms)
            _merge_histogram(item["hist"], row.histogram)
        step_names = {str(step["step_key"]): step["name"] for step in run.scenario_snapshot.get("steps", [])}
        for key, item in groups.items():
            count = item["count"]
            PerfRequestSummary.objects.create(
                run=run, step_key=key, request_name="全部请求" if not key else step_names.get(key, key),
                request_count=count, failure_count=item["failure"],
                avg_ms=Decimal(item["sum"]) / Decimal(count) if count else 0,
                min_ms=item["min"] or 0, max_ms=item["max"] or 0,
                p50_ms=_percentile(item["hist"], .50), p90_ms=_percentile(item["hist"], .90),
                p95_ms=_percentile(item["hist"], .95), p99_ms=_percentile(item["hist"], .99),
                rps=(sum(item["windows"].values(), Decimal("0")) / Decimal(len(item["windows"]))) if item[
                    "windows"] else Decimal("0"),
                max_rps=max(item["windows"].values(), default=Decimal("0")),
                bytes_sent=item["sent"], bytes_received=item["received"],
                histogram=json.dumps(item["hist"], separators=(",", ":")),
            )

    @classmethod
    def _aggregate_stages(cls, run: PerfRun):
        summaries = []
        for index, stage in enumerate(run.scenario_snapshot.get("stages", [])):
            rows = PerfMetricInterval.objects.filter(run=run, scope_type="global", stage_key=stage["stage_key"])
            values = rows.aggregate(requests=Sum("request_count"), failures=Sum("failure_count"),
                                    total=Sum("response_time_sum_ms"))
            count = values["requests"] or 0
            hist = defaultdict(int)
            users_by_window = defaultdict(int)
            for row in rows.iterator(chunk_size=1000):
                _merge_histogram(hist, row.histogram)
                users_by_window[row.window_start.isoformat()] += int((row.actual_load or {}).get("users") or 0)
            actual_users = max(users_by_window.values(), default=0)
            summaries.append({
                "stage_key": stage["stage_key"], "stage_name": stage["name"], "sort": index,
                "target_load": {"users": stage.get("target_users"), "rate": stage.get("target_rate")},
                "actual_load": {"users": actual_users}, "request_count": count,
                "failure_count": values["failures"] or 0,
                "avg_ms": _json_number(Decimal(values["total"] or 0) / Decimal(count) if count else 0),
                "p95_ms": _json_number(_percentile(hist, .95)), "p99_ms": _json_number(_percentile(hist, .99)),
                "rps": _json_number(Decimal(count) / Decimal(max(1, stage["duration_seconds"]))),
                "duration_seconds": stage["duration_seconds"],
            })
        return {"schema_version": 1, "items": summaries}

    @classmethod
    def _evaluate_validity(cls, run: PerfRun) -> bool:
        total_nodes = run.nodes.count()
        successful_nodes = run.nodes.filter(status=PerfRunNodeStatusEnum.SUCCESS.value).count()
        target_users = run.peak_target_users
        load_type = run.scenario_snapshot.get("load_type", "concurrency")
        fixed_count = run.scenario_snapshot.get("load_profile") == "fixed_iterations"
        target_iterations = int(run.scenario_snapshot.get("total_iterations") or 0)
        target_rate = max(
            (Decimal(str(stage.get("target_rate") or 0)) for stage in run.scenario_snapshot.get("stages", [])),
            default=Decimal("0"))
        users_by_window = defaultdict(int)
        window_requests = defaultdict(int)
        peak_cpu = Decimal("0")
        dropped = 0
        iterations = 0
        metric_windows = 0
        for row in PerfMetricInterval.objects.filter(run=run, scope_type="global").iterator(chunk_size=1000):
            users_by_window[row.window_start.isoformat()] += int((row.actual_load or {}).get("users") or 0)
            peak_cpu = max(peak_cpu, Decimal(str((row.generator_metrics or {}).get("cpu_percent") or 0)))
            dropped += row.dropped_count
            iterations += row.iteration_count
            metric_windows += 1
            window_requests[row.window_start.isoformat()] += row.request_count / max(1, row.window_seconds)
        actual_rate = max(window_requests.values(), default=0)
        actual_users = max(users_by_window.values(), default=0)
        expected_windows = max(1, successful_nodes if fixed_count else run.duration_seconds * max(1, successful_nodes))
        metric_coverage = Decimal(metric_windows) / Decimal(expected_windows)
        max_clock_offset = max((abs(node.clock_offset_ms or 0) for node in run.nodes.all()), default=0)
        gates = [
            ("node_completion", "执行节点完整性", successful_nodes == total_nodes and total_nodes > 0, successful_nodes,
             total_nodes),
            ("load_achievement", "目标负载达成率",
             iterations >= target_iterations if fixed_count else
             ((not target_users or actual_users >= target_users * .95) if load_type == "concurrency" else (
                     not target_rate or Decimal(str(actual_rate)) >= target_rate * Decimal("0.95"))),
             iterations if fixed_count else actual_users if load_type == "concurrency" else actual_rate,
             target_iterations if fixed_count else target_users * .95 if load_type == "concurrency" else target_rate * Decimal(
                 "0.95")),
            ("generator_cpu", "发压端 CPU 峰值", peak_cpu <= 90, peak_cpu, 90),
            ("metric_coverage", "实时指标完整率", metric_coverage >= Decimal("0.95"), metric_coverage, Decimal("0.95")),
            ("clock_offset", "执行器时钟偏差", max_clock_offset <= 1000, max_clock_offset, 1000),
            ("dropped_iterations", "丢弃迭代率", not iterations or dropped / iterations <= .01,
             dropped / iterations if iterations else 0, .01),
        ]
        run.validity_results = [{
            "gate_key": key, "name": name,
            "status": PerfValidityStatusEnum.PASSED.value if passed else PerfValidityStatusEnum.FAILED.value,
            "invalidating": True, "actual_value": _json_number(Decimal(str(actual))),
            "required_value": _json_number(Decimal(str(required))), "detail": {},
        } for key, name, passed, actual, required in gates]
        return all(item[2] for item in gates)

    @classmethod
    def _evaluate_performance_goal(cls, run: PerfRun) -> bool:
        summaries = {row.step_key: row for row in PerfRequestSummary.objects.filter(run=run)}
        operators = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b,
                     ">=": lambda a, b: a >= b}
        critical_failed = False
        results = []
        goal = run.scenario_snapshot.get("performance_goal") or PerfPerformanceGoalService.default_payload()
        for config in PerfPerformanceGoalService.to_result_rules(goal):
            summary = summaries.get(config.get("step_key", ""))
            count = summary.request_count if summary else 0
            metric = config["metric"]
            if metric == "error_rate":
                actual = Decimal(summary.failure_count) / Decimal(count) if summary and count else Decimal("0")
            elif metric == "load_achievement_rate":
                actual = cls._load_achievement_rate(run)
            else:
                actual = Decimal(str(getattr(summary, metric, 0) if summary else 0))
            expected = Decimal(str(config["threshold_value"]))
            passed = operators[config["operator"]](actual, expected)
            results.append({
                "threshold_name": config["name"], "scope_type": config["scope_type"], "step_key": "",
                "metric": metric, "operator": config["operator"], "threshold_value": _json_number(expected),
                "actual_value": _json_number(actual), "passed": passed, "severity": config["severity"],
                "evaluated_at": timezone.now().isoformat(), "detail": {"sample_count": count},
            })
            critical_failed |= not passed and config["severity"] == PerfThresholdSeverityEnum.CRITICAL.value
        run.performance_goal_result = {"schema_version": 1, "passed": not critical_failed, "operator": "AND",
                                       "items": results}
        return critical_failed

    @staticmethod
    def _load_achievement_rate(run: PerfRun) -> Decimal:
        rows = PerfMetricInterval.objects.filter(run=run, scope_type="global")
        if run.scenario_snapshot.get("load_profile") == "fixed_iterations":
            target = int(run.scenario_snapshot.get("total_iterations") or 0)
            actual = sum(row.iteration_count for row in rows)
            return min(Decimal("1"), Decimal(actual) / Decimal(target)) if target else Decimal("0")
        if run.scenario_snapshot.get("load_type") == "concurrency":
            by_window = defaultdict(int)
            for row in rows:
                by_window[row.window_start.isoformat()] += int((row.actual_load or {}).get("users") or 0)
            actual = max(by_window.values(), default=0)
            return Decimal(actual) / Decimal(run.peak_target_users) if run.peak_target_users else Decimal("1")
        by_window = defaultdict(Decimal)
        for row in rows:
            by_window[row.window_start.isoformat()] += Decimal(row.request_count) / Decimal(max(1, row.window_seconds))
        actual = max(by_window.values(), default=Decimal("0"))
        target = max((Decimal(str(stage.get("target_rate") or 0)) for stage in run.scenario_snapshot.get("stages", [])),
                     default=Decimal("0"))
        return actual / target if target else Decimal("1")

    @classmethod
    def _certify_capacity(cls, run: PerfRun, valid: bool):
        windows = defaultdict(lambda: {"requests": 0, "users": 0})
        for row in PerfMetricInterval.objects.filter(run=run, scope_type="global").iterator(chunk_size=1000):
            key = row.window_start.isoformat()
            windows[key]["requests"] += row.request_count / max(1, row.window_seconds)
            windows[key]["users"] += int((row.actual_load or {}).get("users") or 0)
        peak_rps = max((value["requests"] for value in windows.values()), default=0)
        peak_users = max((value["users"] for value in windows.values()), default=0)
        target_rps = max(
            (Decimal(str(stage.get("target_rate") or 0)) for stage in run.scenario_snapshot.get("stages", [])),
            default=Decimal("0"))
        checks = [
            {"key": "result_validity", "passed": valid},
            {"key": "node_count", "passed": run.actual_node_count == run.requested_node_count},
            {"key": "target_concurrency", "passed": run.scenario_snapshot.get(
                "load_type") != "concurrency" or not run.peak_target_users or peak_users >= run.peak_target_users * .95},
            {"key": "target_rps", "passed": not target_rps or Decimal(str(peak_rps)) >= target_rps * Decimal("0.95")},
        ]
        run.capacity_result = {
            "schema_version": 1, "target_concurrency": run.peak_target_users,
            "target_rps": _json_number(target_rps), "actual_peak_concurrency": peak_users,
            "actual_peak_rps": _json_number(Decimal(str(peak_rps))), "executor_count": run.actual_node_count,
            "valid": all(item["passed"] for item in checks), "checks": checks,
        }
        return run.capacity_result
