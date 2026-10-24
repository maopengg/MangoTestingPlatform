import base64
import json

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from src.apps.perf.exceptions import (
    PERF_NODE_FAILED,
    PERF_INVALID,
    PERF_PERF_NOT_FOUND,
    PerfError,
)
from src.apps.perf.models import PerfMetricInterval, PerfRun, PerfRunNode
from src.apps.perf.schemas.execution import PerfMetricBatch
from src.apps.perf.services.datetime_utils import normalize_perf_datetime


class PerfMetricService:
    MAX_POINTS = 2000

    @classmethod
    @transaction.atomic
    def ingest(cls, *, node_id: int, batch_data: dict, connection_id: str) -> dict:
        batch = PerfMetricBatch.model_validate(batch_data)
        node = PerfRunNode.objects.select_for_update().select_related("run", "actual_executor_connection").filter(
            id=node_id).first()
        if not node or batch.run_node_id != node.id or batch.run_id != node.run_id:
            raise PerfError(PERF_NODE_FAILED)
        actual_id = str(node.actual_executor_connection.connection_id) if node.actual_executor_connection_id else None
        target_id = str(node.target_executor_connection.connection_id) if node.target_executor_connection_id else None
        if connection_id not in {actual_id, target_id}:
            raise PerfError(PERF_NODE_FAILED)
        rows = []
        existing_rows = PerfMetricInterval.objects.filter(
            run_node=node,
            sequence__in={point.sequence for point in batch.points},
        )
        existing = {
            (row.sequence, row.scope_type, row.scope_key): row
            for row in existing_rows
        }
        for point in batch.points:
            data = point.model_dump(mode="python")
            data["window_start"] = normalize_perf_datetime(data["window_start"])
            candidate = PerfMetricInterval(
                run_id=node.run_id, run_node=node, schema_version=batch.schema_version,
                sequence=data.pop("sequence"), **data,
            )
            key = (candidate.sequence, candidate.scope_type, candidate.scope_key)
            previous = existing.get(key)
            if previous:
                comparable_fields = (
                    "window_seconds", "stage_key", "target_load", "actual_load", "request_count",
                    "failure_count", "iteration_count", "dropped_count", "response_time_sum_ms",
                    "min_response_time_ms", "max_response_time_ms", "bytes_sent", "bytes_received",
                    "connection_count", "connect_error_count", "histogram", "timing_breakdown", "generator_metrics",
                )
                previous_time = previous.window_start.replace(tzinfo=None)
                candidate_time = candidate.window_start.replace(tzinfo=None)
                if previous_time != candidate_time or any(
                        getattr(previous, field) != getattr(candidate, field) for field in comparable_fields):
                    raise PerfError(PERF_INVALID)
                continue
            rows.append(candidate)
        try:
            PerfMetricInterval.objects.bulk_create(rows, ignore_conflicts=False)
        except IntegrityError as exc:
            raise PerfError(PERF_INVALID) from exc
        now = timezone.now()
        node.last_metric_at = now
        node.actual_executor_connection_id = node.actual_executor_connection_id or node.target_executor_connection_id
        node.save(update_fields=["last_metric_at", "actual_executor_connection", "update_time"])
        if rows:
            PerfRun.objects.filter(id=node.run_id).update(revision=F("revision") + 1, update_time=now)
        from src.apps.perf.services.realtime import PerfRealtimeService
        transaction.on_commit(lambda: PerfRealtimeService.notify_run(PerfRun.objects.get(id=node.run_id)))
        return {"accepted": len(rows), "duplicate": len(batch.points) - len(rows),
                "latest_sequence": max(point.sequence for point in batch.points)}

    @classmethod
    def query(cls, *, run_id: int, cursor: str | None = None, max_points: int = 500,
              scope_type: str | None = None, scope_key: str | None = None) -> dict:
        run = PerfRun.objects.filter(id=run_id).first()
        if not run:
            raise PerfError(PERF_PERF_NOT_FOUND)
        after_id = cls.decode_cursor(cursor) if cursor else 0
        queryset = PerfMetricInterval.objects.filter(run_id=run_id, id__gt=after_id)
        if scope_type:
            queryset = queryset.filter(scope_type=scope_type)
        if scope_key:
            queryset = queryset.filter(scope_key=scope_key)
        limit = min(max(1, int(max_points)), cls.MAX_POINTS)
        rows = list(queryset.order_by("id")[:limit + 1])
        has_more = len(rows) > limit
        rows = rows[:limit]
        next_id = rows[-1].id if rows else after_id
        points = [{
            "id": row.id, "node_id": row.run_node_id, "sequence": row.sequence,
            "window_start": row.window_start.isoformat(), "window_seconds": row.window_seconds,
            "scope_type": row.scope_type, "scope_key": row.scope_key, "stage_key": row.stage_key,
            "target_load": row.target_load, "actual_load": row.actual_load,
            "request_count": row.request_count, "failure_count": row.failure_count,
            "iteration_count": row.iteration_count, "dropped_count": row.dropped_count,
            "response_time_sum_ms": row.response_time_sum_ms,
            "min_response_time_ms": row.min_response_time_ms, "max_response_time_ms": row.max_response_time_ms,
            "bytes_sent": row.bytes_sent, "bytes_received": row.bytes_received,
            "connection_count": row.connection_count, "connect_error_count": row.connect_error_count,
            "timing_breakdown": row.timing_breakdown,
            "generator_metrics": row.generator_metrics,
        } for row in rows]
        return {
            "run_id": run.id, "cursor": cls.encode_cursor(next_id), "server_time": timezone.now().isoformat(),
            "has_more": has_more, "points": points, "run_status": run.status, "verdict": run.verdict,
            "revision": run.revision,
        }

    @staticmethod
    def encode_cursor(row_id: int) -> str:
        return base64.urlsafe_b64encode(json.dumps({"v": 1, "id": row_id}).encode()).decode().rstrip("=")

    @staticmethod
    def decode_cursor(cursor: str) -> int:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            value = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
            return int(value["id"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise PerfError(PERF_NODE_FAILED) from exc
