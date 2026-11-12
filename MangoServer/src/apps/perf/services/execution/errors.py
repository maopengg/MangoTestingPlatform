import hashlib
import re

from django.db import transaction

from src.apps.perf.exceptions import (
    PERF_NODE_FAILED,
    PerfError,
)
from src.apps.perf.models import PerfRunError, PerfRunNode
from src.apps.perf.schemas.execution import PerfErrorBatch
from src.apps.perf.services.execution.datetime_utils import normalize_perf_datetime


class PerfErrorService:
    SAMPLE_LIMIT_PER_FINGERPRINT = 20

    @staticmethod
    def _template(message: str) -> str:
        value = re.sub(r"\b[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\b", "{uuid}", message)
        value = re.sub(r"\b\d{3,}\b", "{number}", value)
        return value[:2048]

    @classmethod
    @transaction.atomic
    def ingest(cls, *, node_id: int, batch_data: dict, connection_id: str):
        batch = PerfErrorBatch.model_validate(batch_data)
        node = PerfRunNode.objects.select_for_update().select_related(
            "target_executor_connection", "actual_executor_connection"
        ).filter(id=node_id).first()
        if not node or batch.run_id != node.run_id or batch.run_node_id != node.id:
            raise PerfError(PERF_NODE_FAILED)
        allowed = {
            str(node.target_executor_connection.connection_id) if node.target_executor_connection_id else None,
            str(node.actual_executor_connection.connection_id) if node.actual_executor_connection_id else None,
        }
        if connection_id not in allowed:
            raise PerfError(PERF_NODE_FAILED)
        accepted = 0
        duplicates = 0
        for payload in batch.samples:
            template = cls._template(payload.message)
            occurred_at = normalize_perf_datetime(payload.occurred_at)
            raw = "|".join((payload.step_key, payload.error_type, payload.error_code, template))
            fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            aggregate, _ = PerfRunError.objects.get_or_create(
                run_id=node.run_id, step_key=payload.step_key, fingerprint=fingerprint,
                defaults={
                    "error_type": payload.error_type, "error_code": payload.error_code,
                    "message_template": template, "count": 0,
                    "first_seen_at": occurred_at, "last_seen_at": occurred_at,
                },
            )
            aggregate = PerfRunError.objects.select_for_update().get(id=aggregate.id)
            samples = list(aggregate.samples or [])
            if any(item.get("sample_key") == payload.sample_key and item.get("run_node_id") == node.id for item in
                   samples):
                duplicates += 1
                continue
            aggregate.count += 1
            aggregate.first_seen_at = min(aggregate.first_seen_at, occurred_at)
            aggregate.last_seen_at = max(aggregate.last_seen_at, occurred_at)
            if len(samples) < cls.SAMPLE_LIMIT_PER_FINGERPRINT:
                samples.append({
                    "sample_key": payload.sample_key, "run_node_id": node.id,
                    "occurred_at": occurred_at.isoformat(), "request_summary": payload.request_summary,
                    "response_status": payload.response_status, "response_excerpt": payload.response_excerpt,
                    "elapsed_ms": payload.elapsed_ms,
                })
            accepted += 1
            aggregate.samples = samples
            aggregate.node_ids = sorted({*(aggregate.node_ids or []), node.id})
            aggregate.node_count = len(aggregate.node_ids)
            aggregate.save(update_fields=["count", "first_seen_at", "last_seen_at", "samples", "node_ids", "node_count",
                                          "update_time"])
        return {"accepted": accepted, "duplicate": duplicates}
