import os
import socket
from datetime import timedelta

from django.utils import timezone

from src.apps.monitoring.selectors.querysets import MonitoringQuerySelector
from src.apps.system.enums import RuntimeServiceName


class ApiWorkerReadinessService:
    @staticmethod
    def ready():
        pod_uid = os.getenv('POD_UID')
        if not pod_uid:
            return False
        row = MonitoringQuerySelector.service_heartbeats().filter(
            service_name=RuntimeServiceName.API_WORKER.value,
            host_name=socket.gethostname(), status=1,
            last_seen_at__gte=timezone.now() - timedelta(seconds=45),
        ).values('metadata').first()
        metadata = (row or {}).get('metadata') or {}
        return (metadata.get('pod_uid') == pod_uid
                and metadata.get('execution_loop_alive') is True
                and metadata.get('executor_threads_alive') is True
                and metadata.get('datasource_maintenance_healthy') is True)
