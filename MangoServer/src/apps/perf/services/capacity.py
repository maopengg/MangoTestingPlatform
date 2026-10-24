import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal

import math
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from src.apps.perf.enums import PerfLoadTypeEnum, PerfReservationStatusEnum
from src.apps.perf.exceptions import (
    PERF_EXECUTOR_EXECUTION_INVALID,
    PERF_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID,
    PERF_EXECUTOR_EXECUTION_PERF_REQUIRED,
    PerfError,
)
from src.apps.perf.models import PerfRun, PerfRunNode
from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.models import SocketConnection


class PerfCapacityService:
    """按稳定执行器节点标识锁定容量；连接 UUID 只记录本次会话。"""

    DEFAULT_UNCALIBRATED_SAFE_VUS = 100
    DEFAULT_UNCALIBRATED_SAFE_RPS = Decimal("20")
    SAFETY_FACTOR = Decimal("0.70")
    MAX_CONCURRENT_RUNS_PER_EXECUTOR = 5

    @classmethod
    def max_concurrent_runs_per_executor(cls) -> int:
        return SystemConfigService.get_ranged_int('PERF_EXECUTOR_MAX_CONCURRENT_RUNS')

    @classmethod
    def capacity_overview(cls):
        """Return the operator-facing capacity view without exposing connection internals."""
        now = timezone.now()
        online = {
            fingerprint: (connection, capability_capacity)
            for fingerprint, connection, capability_capacity in cls._online_perf_executors()
        }

        reserved_by_executor = {}
        reservations = (
            PerfRunNode.objects.filter(
                reservation_status__in=[PerfReservationStatusEnum.RESERVED.value,
                                        PerfReservationStatusEnum.CLAIMED.value],
                lease_expires_at__gt=now,
            )
            .values("executor_fingerprint", "capacity_type")
            .annotate(value=Sum("reserved_value"))
        )
        for reservation in reservations:
            reserved_by_executor[
                (reservation["executor_fingerprint"], reservation["capacity_type"])
            ] = Decimal(reservation["value"] or 0)

        fingerprints = set(online)
        rows = []
        for fingerprint in fingerprints:
            online_entry = online.get(fingerprint)
            connection, capability_capacity = online_entry or (None, cls.max_concurrent_runs_per_executor())
            safe_vus = Decimal(cls.DEFAULT_UNCALIBRATED_SAFE_VUS)
            safe_rps = cls.DEFAULT_UNCALIBRATED_SAFE_RPS
            reserved_vus = reserved_by_executor.get((fingerprint, "vu"), Decimal("0"))
            reserved_rps = reserved_by_executor.get((fingerprint, "rps"), Decimal("0"))
            owner = connection.user if connection else None
            rows.append({
                "fingerprint": fingerprint,
                "executor_name": (owner.name or owner.username) if owner else fingerprint,
                "online": bool(connection),
                "connection_id": connection.id if connection else None,
                "last_seen_at": connection.last_seen_at if connection else None,
                "engine": "k6",
                "engine_version": None,
                "calibrated": False,
                "calibration_status": "safe_default",
                "safe_vus": int(safe_vus),
                "safe_rps": float(safe_rps),
                "reserved_vus": float(reserved_vus),
                "reserved_rps": float(reserved_rps),
                "available_vus": float(max(Decimal("0"), safe_vus * cls.SAFETY_FACTOR - reserved_vus)),
                "available_rps": float(max(Decimal("0"), safe_rps * cls.SAFETY_FACTOR - reserved_rps)),
                "safety_factor": float(cls.SAFETY_FACTOR),
                "max_concurrent_runs": capability_capacity,
                "valid_until": None, "calibrated_at": None, "source": "safe_default",
            })

        rows.sort(key=lambda item: (not item["online"], item["executor_name"], item["fingerprint"]))
        return {
            "summary": {
                "executor_count": len(rows),
                "online_count": sum(item["online"] for item in rows),
                "calibrated_count": sum(item["calibrated"] for item in rows),
                "available_vus": sum(item["available_vus"] for item in rows if item["online"]),
                "available_rps": sum(item["available_rps"] for item in rows if item["online"]),
            },
            "defaults": {
                "safe_vus": cls.DEFAULT_UNCALIBRATED_SAFE_VUS,
                "safe_rps": float(cls.DEFAULT_UNCALIBRATED_SAFE_RPS),
                "safety_factor": float(cls.SAFETY_FACTOR),
            },
            "rows": rows,
        }

    @classmethod
    def list_available_executors(cls):
        rows = []
        for fingerprint, connection, capability_capacity in cls._online_perf_executors():
            rows.append({
                "fingerprint": fingerprint,
                "executor_name": connection.user.name or connection.user.username,
                "capability_capacity": capability_capacity,
                "last_seen_at": connection.last_seen_at,
            })
        return rows

    @classmethod
    def estimate_snapshot(cls, *, engine: str, snapshot: dict, requested_node_count: int, policy: dict):
        now = timezone.now()
        load_type = snapshot.get("load_type", PerfLoadTypeEnum.CONCURRENCY.value)
        capacity_type = "vu" if load_type == PerfLoadTypeEnum.CONCURRENCY.value else "rps"
        requested = Decimal(
            max((stage.get("target_users") or stage.get("max_vus") or 0 for stage in snapshot.get("stages", [])),
                default=0))
        if capacity_type == "rps":
            requested = max((Decimal(str(stage.get("target_rate") or 0)) for stage in snapshot.get("stages", [])),
                            default=Decimal("0"))
        safety_factor = Decimal(str((policy or {}).get("capacity_safety_factor", cls.SAFETY_FACTOR)))
        specified_values = list(dict.fromkeys((policy or {}).get("specified_executor_fingerprints") or []))
        specified = set(specified_values) if (policy or {}).get("mode") == "specified" else set()
        capacities = []
        for fingerprint, connection, capability_capacity in cls._online_perf_executors():
            safe = Decimal(
                cls.DEFAULT_UNCALIBRATED_SAFE_VUS if capacity_type == "vu" else cls.DEFAULT_UNCALIBRATED_SAFE_RPS
            )
            reserved = PerfRunNode.objects.filter(
                executor_fingerprint=fingerprint, capacity_type=capacity_type,
                reservation_status__in=[PerfReservationStatusEnum.RESERVED.value,
                                        PerfReservationStatusEnum.CLAIMED.value],
                lease_expires_at__gt=now,
            ).aggregate(value=Sum("reserved_value"))["value"] or Decimal("0")
            active_run_count = PerfRunNode.objects.filter(
                executor_fingerprint=fingerprint,
                reservation_status__in=[PerfReservationStatusEnum.RESERVED.value,
                                        PerfReservationStatusEnum.CLAIMED.value],
                lease_expires_at__gt=now,
            ).values("run_id").distinct().count()
            if active_run_count >= capability_capacity:
                continue
            capacities.append({
                "fingerprint": fingerprint,
                "executor_name": connection.user.name or connection.user.username,
                "available": max(Decimal("0"), safe * safety_factor - reserved),
                "calibrated": False,
                "last_seen_at": connection.last_seen_at.isoformat(),
            })
        capacities.sort(key=lambda value: value["available"], reverse=True)
        capacity_by_fingerprint = {item["fingerprint"]: item for item in capacities}
        selected = [capacity_by_fingerprint[value] for value in specified_values if value in capacity_by_fingerprint]
        per_node = Decimal(math.ceil(requested / max(1, requested_node_count)))
        selection_valid = (
                (policy or {}).get("mode") == "specified"
                and len(specified_values) == requested_node_count
                and len(selected) == requested_node_count
        )
        can_run = selection_valid and all(item["available"] >= per_node for item in selected)
        return {
            "can_run": can_run, "capacity_type": capacity_type, "required": float(requested),
            "required_per_node": float(per_node), "requested_node_count": requested_node_count,
            "online_candidate_count": len(capacities),
            "available_selected": float(sum((item["available"] for item in selected), Decimal("0"))),
            "uncalibrated_selected_count": sum(not item["calibrated"] for item in selected),
            "selection_required": True, "selection_valid": selection_valid,
            "candidates": [{**item, "available": float(item["available"])} for item in capacities],
            "selected": [{**item, "available": float(item["available"])} for item in selected],
        }

    @classmethod
    @transaction.atomic
    def reserve(cls, run: PerfRun):
        now = timezone.now()
        PerfRunNode.objects.select_for_update().filter(
            reservation_status__in=[PerfReservationStatusEnum.RESERVED.value, PerfReservationStatusEnum.CLAIMED.value],
            lease_expires_at__lte=now,
        ).update(reservation_status=PerfReservationStatusEnum.EXPIRED.value, update_time=now)
        online = cls._online_perf_executors()
        if not online:
            raise PerfError(PERF_EXECUTOR_EXECUTION_INVALID)
        candidates = []
        load_type = run.scenario_snapshot.get("load_type", PerfLoadTypeEnum.CONCURRENCY.value)
        capacity_type = "vu" if load_type == PerfLoadTypeEnum.CONCURRENCY.value else "rps"
        policy = run.execution_policy or {}
        safety_factor = Decimal(str(policy.get("capacity_safety_factor", cls.SAFETY_FACTOR)))
        specified_values = list(dict.fromkeys(policy.get("specified_executor_fingerprints") or []))
        if policy.get("mode") != "specified" or len(specified_values) != run.requested_node_count:
            raise PerfError(PERF_EXECUTOR_EXECUTION_PERF_REQUIRED,
                            value=(run.requested_node_count, len(specified_values)))
        specified = set(specified_values)
        for fingerprint, connection, capability_capacity in online:
            connection = SocketConnection.objects.select_for_update().select_related("user").get(id=connection.id)
            if specified and fingerprint not in specified:
                continue
            safe = Decimal(
                cls.DEFAULT_UNCALIBRATED_SAFE_VUS if capacity_type == "vu"
                else cls.DEFAULT_UNCALIBRATED_SAFE_RPS
            )
            reserved = PerfRunNode.objects.select_for_update().filter(
                executor_fingerprint=fingerprint,
                reservation_status__in=[PerfReservationStatusEnum.RESERVED.value,
                                        PerfReservationStatusEnum.CLAIMED.value],
                lease_expires_at__gt=now, capacity_type=capacity_type,
            ).aggregate(value=Sum("reserved_value"))["value"] or Decimal("0")
            active_run_count = PerfRunNode.objects.filter(
                executor_fingerprint=fingerprint,
                reservation_status__in=[PerfReservationStatusEnum.RESERVED.value,
                                        PerfReservationStatusEnum.CLAIMED.value],
                lease_expires_at__gt=now,
            ).values("run_id").distinct().count()
            if active_run_count >= capability_capacity:
                continue
            available = max(Decimal("0"), safe * safety_factor - reserved)
            candidates.append((available, fingerprint, connection))
        candidates.sort(key=lambda item: (item[0], item[2].last_seen_at), reverse=True)
        node_count = min(run.requested_node_count, len(candidates))
        if node_count < run.requested_node_count:
            raise PerfError(PERF_EXECUTOR_EXECUTION_INVALID)
        requested = Decimal(run.peak_target_users)
        if capacity_type == "rps":
            requested = max(
                (Decimal(str(stage.get("target_rate") or 0)) for stage in run.scenario_snapshot.get("stages", [])),
                default=Decimal("0"))
        per_node = Decimal(math.ceil(requested / max(1, node_count)))
        selected = candidates[:node_count]
        total_available = sum((item[0] for item in selected), Decimal("0"))
        required = per_node * node_count
        if any(item[0] < per_node for item in selected):
            raise PerfError(PERF_EXECUTOR_EXECUTION_INVALID_CODE_EXECUTOR_EXECUTION_INVALID,
                            value=(str(required), str(total_available)))
        nodes = []
        for index, (_, fingerprint, connection) in enumerate(selected):
            token = secrets.token_urlsafe(32)
            node = PerfRunNode.objects.create(
                run=run, shard_index=index, shard_count=node_count, executor_fingerprint=fingerprint,
                target_executor_connection=connection, status="reserved",
                capacity_type=capacity_type, reserved_value=per_node,
                reservation_status=PerfReservationStatusEnum.RESERVED.value,
                lease_token_hash=hashlib.sha256(token.encode()).hexdigest(),
                lease_expires_at=now + timedelta(seconds=max(run.duration_seconds + 900, 1800)),
            )
            nodes.append(node)
        return nodes

    @classmethod
    def _online_perf_executors(cls):
        rows = []
        seen_users = set()
        for connection in SocketConnectionService.list_online_actuators():
            if connection.user_id in seen_users:
                continue
            if (
                    not connection.is_open
                    or SocketConnectionService.is_draining(connection.connection_id)
                    or not SocketConnectionService.supports_task_type(
                connection.connection_id, ExecutorTaskTypeEnum.PERF_EXECUTION.value,
            )
            ):
                continue
            seen_users.add(connection.user_id)
            capability_capacity = SocketConnectionService.capability_capacity(
                connection.connection_id,
                "perf",
                cls.max_concurrent_runs_per_executor(),
            )
            if capability_capacity <= 0:
                continue
            rows.append((f"user:{connection.user_id}", connection, capability_capacity))
        return rows

    @staticmethod
    def release(run_id: int):
        PerfRunNode.objects.filter(
            run_id=run_id,
            reservation_status__in=[PerfReservationStatusEnum.RESERVED.value, PerfReservationStatusEnum.CLAIMED.value],
        ).update(reservation_status=PerfReservationStatusEnum.RELEASED.value, update_time=timezone.now())

    @staticmethod
    def expire():
        now = timezone.now()
        return PerfRunNode.objects.filter(
            reservation_status__in=[PerfReservationStatusEnum.RESERVED.value, PerfReservationStatusEnum.CLAIMED.value],
            lease_expires_at__lte=now,
        ).update(reservation_status=PerfReservationStatusEnum.EXPIRED.value, update_time=now)
