import os
import socket
from datetime import timedelta

from django.utils import timezone

from src.apps.monitoring.selectors.querysets import MonitoringQuerySelector
from src.apps.system.enums import RuntimeServiceName


class SchedulerReadinessService:
    @staticmethod
    def ready():
        filters = {'service_name': RuntimeServiceName.SCHEDULER.value,
                   'host_name': socket.gethostname(), 'status': 1,
                   'last_seen_at__gte': timezone.now() - timedelta(seconds=45)}
        if os.getenv('MANGO_SERVICE_INSTANCE'):
            filters['instance_name'] = os.environ['MANGO_SERVICE_INSTANCE']
        row = MonitoringQuerySelector.service_heartbeats().filter(**filters).values('metadata').first()
        # 旧版本心跳或其他容器的心跳不能证明当前清理线程已启动。
        if not row or (row['metadata'] or {}).get('cleanup_consumers_alive') is not True:
            return False
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
        if row['metadata'].get('cleanup_consumer_threads') != DatasourceGovernorService.policy().cleanup_consumer_threads:
            return False
        if row['metadata'].get('datasource_maintenance_healthy') is not True:
            return False
        store = DatasourceGovernorService.store()
        with store.control_connection():
            store.get_entry('health-readonly')
        return True
