from datetime import timedelta

from django.utils import timezone
from mangotools.enums import StatusEnum

from src.apps.monitoring.models import ServiceHeartbeat
from src.apps.system.enums import RuntimeServiceName


class ExecutionCapacitySelector:
    @staticmethod
    def api_workers():
        # Only aggregate capacity is exposed to business pages, never host/pod identities or logs.
        rows = ServiceHeartbeat.objects.filter(
            service_name=RuntimeServiceName.API_WORKER.value, status=StatusEnum.SUCCESS.value,
            last_seen_at__gte=timezone.now() - timedelta(seconds=60),
        ).values_list('metadata', flat=True)
        capacity = running = online = 0
        for metadata in rows:
            metadata = metadata if isinstance(metadata, dict) else {}
            online += 1
            capacity += max(0, int(metadata.get('claim_limit') or 0))
            running += max(0, int(metadata.get('running_count') or 0))
        return {'online': online, 'capacity': capacity, 'running': running}
