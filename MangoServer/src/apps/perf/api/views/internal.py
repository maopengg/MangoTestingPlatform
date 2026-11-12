import time
from django.db import transaction
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.perf.enums import PerfNodeFailurePolicyEnum, PerfReservationStatusEnum, PerfRunNodeStatusEnum, \
    PerfRunStatusEnum
from src.apps.perf.exceptions import (
    PERF_NODE_FAILED,
    PerfError,
)
from src.apps.perf.models import PerfRunEvent, PerfRunNode
from src.apps.perf.services import PerfErrorService, PerfMetricService, PerfSecretService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0082


class PerfRunNodeViews(ViewSet):
    """执行器内部协议；连接归属和任务租约是授权事实。"""

    @staticmethod
    def _connection_id(request: Request) -> str:
        value = request.headers.get("X-Executor-Connection-Id") or request.data.get("connection_id")
        if not value:
            raise PerfError(PERF_NODE_FAILED)
        return str(value)

    @classmethod
    def _node(cls, request: Request, pk) -> PerfRunNode:
        node = PerfRunNode.objects.select_related("run", "target_executor_connection", "actual_executor_connection",
                                                  "executor_task").filter(id=pk).first()
        if not node:
            raise PerfError(PERF_NODE_FAILED)
        connection_id = cls._connection_id(request)
        allowed = {
            str(node.target_executor_connection.connection_id) if node.target_executor_connection_id else None,
            str(node.actual_executor_connection.connection_id) if node.actual_executor_connection_id else None,
        }
        if connection_id not in allowed:
            raise PerfError(PERF_NODE_FAILED)
        user = getattr(getattr(request, "user", None), "user_obj", None)
        allowed_user_ids = {
            node.target_executor_connection.user_id if node.target_executor_connection_id else None,
            node.actual_executor_connection.user_id if node.actual_executor_connection_id else None,
        }
        if user is None or user.id not in allowed_user_ids:
            raise PerfError(PERF_NODE_FAILED)
        return node

    @error_response("system")
    def ready(self, request, pk=None):
        """上报性能测试节点就绪状态"""
        with transaction.atomic():
            node = self._node(request, pk)
            node.actual_executor_connection = node.target_executor_connection
            node.status = PerfRunNodeStatusEnum.READY.value
            node.ready_at = timezone.now()
            node.engine_version = str(request.data.get("engine_version", ""))[:32]
            node.clock_offset_ms = request.data.get("clock_offset_ms")
            node.reservation_status = PerfReservationStatusEnum.CLAIMED.value
            node.save(update_fields=["actual_executor_connection", "status", "reservation_status", "ready_at",
                                     "engine_version", "clock_offset_ms", "update_time"])
            PerfRunEvent.objects.create(run=node.run, run_node=node, event_type="node_ready", message="性能节点已就绪",
                                        detail={}, occurred_at=timezone.now())
            policy = node.run.execution_policy or {}
            ready_statuses = [PerfRunNodeStatusEnum.READY.value, PerfRunNodeStatusEnum.RUNNING.value]
            ready_count = node.run.nodes.filter(status__in=ready_statuses).count()
            all_ready = not node.run.nodes.exclude(status__in=ready_statuses).exists()
            allow_partial = (
                    policy.get("node_failure_policy") == PerfNodeFailurePolicyEnum.CONTINUE.value
                    and ready_count >= int(policy.get("min_ready_nodes", node.run.requested_node_count))
            )
            if node.run.status != PerfRunStatusEnum.RUNNING.value and (all_ready or allow_partial):
                node.run.status = PerfRunStatusEnum.RUNNING.value
                node.run.started_at = node.run.started_at or node.ready_at
                node.run.revision += 1
                node.run.save(update_fields=["status", "started_at", "revision", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, {"node_id": node.id, "schedule_at": node.run.schedule_at,
                                                        "control_revision": node.control_revision})

    @error_response("system")
    def control(self, request, pk=None):
        """获取性能测试节点控制指令"""
        node = self._node(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, {
            "control_revision": node.control_revision,
            "action": "stop" if node.run.stop_requested_at else "run",
            "run_status": node.run.status,
            "server_epoch_ms": int(time.time() * 1000),
        })

    @error_response("system")
    def heartbeat(self, request, pk=None):
        """上报性能测试执行节点心跳"""
        node = self._node(request, pk)
        node.last_heartbeat_at = timezone.now()
        node.engine_pid = request.data.get("engine_pid")
        if node.status == PerfRunNodeStatusEnum.READY.value and node.engine_pid is not None:
            node.status = PerfRunNodeStatusEnum.RUNNING.value
            node.started_at = node.started_at or node.last_heartbeat_at
        node.save(update_fields=["last_heartbeat_at", "engine_pid", "status", "started_at", "update_time"])
        return ResponseData.success(RESPONSE_MSG_0082, {"control_revision": node.control_revision,
                                                        "stop_requested": bool(node.run.stop_requested_at)})

    @error_response("system")
    def metrics(self, request, pk=None):
        """接收性能测试节点指标"""
        data = PerfMetricService.ingest(node_id=int(pk), batch_data=request.data,
                                        connection_id=self._connection_id(request))
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @error_response("system")
    def errors(self, request, pk=None):
        """接收性能测试节点错误"""
        data = PerfErrorService.ingest(node_id=int(pk), batch_data=request.data,
                                       connection_id=self._connection_id(request))
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @error_response("system")
    def secrets(self, request, pk=None):
        """获取性能测试节点执行所需凭据"""
        node = self._node(request, pk)
        return ResponseData.success(RESPONSE_MSG_0001, {"values": PerfSecretService.reveal_for_node(node)})

    @error_response("system")
    def result(self, request, pk=None):
        """上报性能测试执行节点执行结果"""
        with transaction.atomic():
            node = self._node(request, pk)
            if node.status in PerfRunNodeStatusEnum.terminal_values():
                return ResponseData.success(RESPONSE_MSG_0082, {
                    "node_id": node.id, "status": node.status, "run_status": node.run.status, "duplicate": True,
                })
            status = str(request.data.get("status", PerfRunNodeStatusEnum.FAILED.value))
            if status not in PerfRunNodeStatusEnum.terminal_values():
                raise PerfError(PERF_NODE_FAILED)
            node.status = status
            node.finished_at = timezone.now()
            node.resource_summary = request.data.get("resource_summary") or {}
            node.result_summary = request.data.get("result_summary") or {}
            node.error_code = request.data.get("error_code")
            node.error_message = str(request.data.get("error_message") or "")[:2048]
            node.save(update_fields=["status", "finished_at", "resource_summary", "result_summary", "error_code",
                                     "error_message", "update_time"])
            PerfRunEvent.objects.create(run=node.run, run_node=node, event_type="node_finished",
                                        message="性能节点已结束", detail={"status": status},
                                        occurred_at=node.finished_at)
            if not node.run.nodes.exclude(status__in=PerfRunNodeStatusEnum.terminal_values()).exists():
                failed = node.run.nodes.exclude(status=PerfRunNodeStatusEnum.SUCCESS.value).exists()
                node.run.status = PerfRunStatusEnum.AGGREGATING.value
                node.run.finished_at = node.finished_at
                node.run.summary = {"node_count": node.run.nodes.count(), "has_node_failure": failed}
                node.run.revision += 1
                node.run.save(update_fields=["status", "finished_at", "summary", "revision", "update_time"])
                from src.apps.perf.services.execution.recovery import PerfRecoveryService
                transaction.on_commit(lambda: PerfRecoveryService.safe_finalize(node.run_id))
        return ResponseData.success(RESPONSE_MSG_0082,
                                    {"node_id": node.id, "status": node.status, "run_status": node.run.status})
