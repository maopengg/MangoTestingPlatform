import copy
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from src.apps.perf.enums import PerfRunNodeStatusEnum, PerfRunStatusEnum, PerfRunVerdictEnum
from src.apps.perf.exceptions import (
    PERF_STATUS_EXECUTION_NOT_ALLOWED,
    PERF_PERF_NOT_FOUND,
    PERF_EXECUTOR_EXECUTION_PERF_REQUIRED,
    PerfError,
)
from src.apps.perf.models import PerfRun, PerfRunEvent, PerfScenario
from src.apps.perf.schemas.execution import PerfExecutorPolicy, PerfScenarioIR
from src.apps.perf.services.capacity import PerfCapacityService
from src.apps.perf.services.compiler import PerfScenarioCompiler, snapshot_hash
from src.apps.perf.services.secrets import PerfSecretService
from src.apps.system.enums import ExecutorModeEnum, ExecutorTaskTypeEnum
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.services.factory import func_test_object_value
from src.apps.test_center.services.test_target import TestTargetService


class PerfExecutionService:
    @staticmethod
    def _validate_executor_selection(required_count: int, selected: list[str] | None) -> list[str]:
        values = list(dict.fromkeys(selected or []))
        if len(values) != required_count:
            raise PerfError(PERF_EXECUTOR_EXECUTION_PERF_REQUIRED, value=(required_count, len(values)))
        return values

    @staticmethod
    def _event(run: PerfRun, event_type: str, message: str, *, node=None, detail=None):
        PerfRunEvent.objects.create(run=run, run_node=node, event_type=event_type, message=message,
                                    detail=detail or {}, occurred_at=timezone.now())

    @staticmethod
    def _bind_environment(snapshot: dict, *, test_env: int, project_product_id: int) -> dict:
        result = copy.deepcopy(snapshot)
        result["test_env"] = test_env
        test_object = func_test_object_value(test_env, project_product_id, AutoTypeEnum.API.value)
        base_url = TestTargetService.resolve(test_object)
        for step in result.get("steps", []):
            step.setdefault("request", {})["base_url"] = base_url
        return PerfScenarioIR.model_validate(result).model_dump(mode="json")

    @classmethod
    @transaction.atomic
    def create_direct_run(
            cls,
            *,
            scenario_id: int,
            user,
            test_env: int,
            selected_executor_fingerprints: list[str],
            remark: str = "",
            capture_request: bool = False,
            capture_response: bool = False,
    ) -> PerfRun:
        scenario = PerfScenario.objects.select_for_update().filter(id=scenario_id, status=1).first()
        if not scenario:
            raise PerfError(PERF_PERF_NOT_FOUND)
        selected_executor_fingerprints = cls._validate_executor_selection(
            scenario.default_executor_count, selected_executor_fingerprints,
        )
        ir, ir_hash, runtime_secrets = PerfScenarioCompiler.compile_with_secrets(scenario)
        ir = cls._bind_environment(ir, test_env=test_env, project_product_id=scenario.project_product_id)
        ir_hash = snapshot_hash(ir)
        run = PerfRun.objects.create(
            scenario=scenario, name=scenario.name,
            created_by=user, project_product=scenario.project_product, module=scenario.module,
            test_env=test_env, test_env_title=EnvironmentEnum.obj().get(test_env, "未知环境"), engine=ir["engine"],
            schema_version=ir["schema_version"], scenario_snapshot=ir, snapshot_hash=ir_hash,
            requested_node_count=scenario.default_executor_count,
            peak_target_users=max((stage.get("target_users") or stage.get("max_vus") or 0 for stage in ir["stages"]),
                                  default=0),
            duration_seconds=sum(stage["duration_seconds"] for stage in ir["stages"]), remark=remark,
            execution_policy=PerfExecutorPolicy(
                mode="specified",
                specified_executor_fingerprints=selected_executor_fingerprints,
                min_ready_nodes=scenario.min_ready_nodes or scenario.default_executor_count,
                node_failure_policy=scenario.node_failure_policy,
            ).model_dump(mode="json") | {"capture": {"request": capture_request, "response": capture_response}},
        )
        cls._event(run, "run_created", "性能运行已创建")
        PerfSecretService.seal(run, runtime_secrets)
        return run

    @classmethod
    @transaction.atomic
    def dispatch_run(cls, run_id: int, *, delay_seconds: int = 0) -> PerfRun:
        run = PerfRun.objects.select_for_update().select_related("created_by").filter(id=run_id).first()
        if not run:
            raise PerfError(PERF_PERF_NOT_FOUND)
        if run.status not in {PerfRunStatusEnum.CREATED.value, PerfRunStatusEnum.QUEUED.value,
                              PerfRunStatusEnum.WAITING_EXECUTOR.value}:
            raise PerfError(PERF_STATUS_EXECUTION_NOT_ALLOWED)
        nodes = PerfCapacityService.reserve(run)
        selected = [node.target_executor_connection for node in nodes]
        delay_seconds = max(0, int(delay_seconds))
        schedule_at = timezone.now() + timedelta(seconds=5 + delay_seconds)
        PerfSecretService.extend_for_dispatch(run, schedule_at)
        run.nodes.update(
            lease_expires_at=schedule_at + timedelta(seconds=run.duration_seconds + 900)
        )
        for index, connection in enumerate(selected):
            node = nodes[index]
            node.status = PerfRunNodeStatusEnum.DISPATCHED.value
            node.allocated_load = {"shard_index": index, "shard_count": len(selected)}
            node.save(update_fields=["status", "allocated_load", "update_time"])
            task = ExecutorTaskService.create(
                task_type=ExecutorTaskTypeEnum.PERF_EXECUTION.value, created_by=run.created_by,
                executor_mode=ExecutorModeEnum.SPECIFIED.value, executor_user=connection.user,
                target_executor_connection=connection, business_type="perf_run_node", business_id=node.id,
                message_key=f"perf-run-node:{node.id}",
                execution_timeout_seconds=max(run.duration_seconds + delay_seconds + 900, 1800),
                schedule_timeout_seconds=300,
                payload={"schema_version": 1, "func_name": "perf_execution", "func_args": {
                    "run_id": run.id, "run_node_id": node.id, "node_key": str(node.node_key),
                    "schedule_at": schedule_at.isoformat(), "schedule_at_epoch_ms": int(schedule_at.timestamp() * 1000),
                    "scenario": run.scenario_snapshot,
                    "variables": (run.execution_policy or {}).get("runtime_variables", {}),
                    "capture": (run.execution_policy or {}).get("capture", {"request": False, "response": False}),
                    "shard_index": index, "shard_count": len(selected),
                }},
            )
            node.executor_task = task
            node.save(update_fields=["executor_task", "update_time"])
            cls._event(run, "node_dispatched", "性能节点任务已下发", node=node,
                       detail={"shard_index": index, "shard_count": len(selected)})
        run.status = PerfRunStatusEnum.STARTING.value
        run.schedule_at = schedule_at
        run.actual_node_count = len(selected)
        run.revision += 1
        run.save(update_fields=["status", "schedule_at", "actual_node_count", "revision", "update_time"])
        return run

    @classmethod
    @transaction.atomic
    def request_stop(cls, run_id: int, *, cancel: bool = False) -> PerfRun:
        run = PerfRun.objects.select_for_update().filter(id=run_id).first()
        if not run:
            raise PerfError(PERF_PERF_NOT_FOUND)
        if run.status in PerfRunStatusEnum.terminal_values():
            return run
        run.stop_requested_at = timezone.now()
        cancelled_before_start = cancel and not run.started_at
        run.status = PerfRunStatusEnum.CANCELLED.value if cancelled_before_start else PerfRunStatusEnum.STOPPING.value
        if cancelled_before_start:
            run.verdict = PerfRunVerdictEnum.INVALID.value
            run.finished_at = timezone.now()
        run.revision += 1
        run.save(update_fields=["stop_requested_at", "status", "verdict", "finished_at", "revision", "update_time"])
        for node in run.nodes.select_related("executor_task").all():
            node.control_revision += 1
            if cancelled_before_start:
                node.status = PerfRunNodeStatusEnum.CANCELLED.value
                node.finished_at = timezone.now()
            node.save(update_fields=["control_revision", "status", "finished_at", "update_time"])
            if node.executor_task_id:
                ExecutorTaskService.cancel(node.executor_task_id, run.created_by_id)
        if cancelled_before_start:
            PerfCapacityService.release(run.id)
        cls._event(run, "cancel_requested" if cancel else "stop_requested",
                   "用户请求取消性能运行" if cancel else "用户请求停止性能运行")
        from src.apps.perf.services.realtime import PerfRealtimeService
        transaction.on_commit(lambda: PerfRealtimeService.notify_run(run))
        return run
