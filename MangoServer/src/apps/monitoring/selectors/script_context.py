from datetime import timedelta

from django.utils import timezone
from pydantic import ValidationError

from src.apps.monitoring.models import ServiceHeartbeat
from src.apps.monitoring.schemas.script_context import MonitoringScriptCapabilities
from src.apps.monitoring.constants import SCRIPT_DEPENDENCIES
from src.apps.system.enums import RuntimeServiceName


class MonitoringScriptContextSelector:
    @staticmethod
    def get():
        # 只读取 monitoring-service 心跳，不探测 MCP/Web 进程的 Python 环境。
        metadata_rows = list(ServiceHeartbeat.objects.filter(
            service_name=RuntimeServiceName.MONITORING.value, status=1,
            last_seen_at__gte=timezone.now() - timedelta(seconds=60),
        ).values_list('metadata', flat=True))
        capabilities = []
        for metadata in metadata_rows:
            payload = metadata.get('monitoring_script_capabilities') if isinstance(metadata, dict) else None
            try:
                item = MonitoringScriptCapabilities.model_validate(payload)
                if item.version == 1:
                    capabilities.append(item)
            except ValidationError:
                continue
        unknown = len(metadata_rows) - len(capabilities)
        packages = []
        for name, _ in SCRIPT_DEPENDENCIES:
            observed = [item.packages[name] for item in capabilities if name in item.packages]
            complete = bool(metadata_rows) and not unknown and len(observed) == len(capabilities)
            packages.append({
                'module': name,
                'available_on_all_online_nodes': all(value is not None for value in observed) if complete else None,
                'versions': sorted({value for value in observed if value is not None}),
                'reported_nodes': len(observed),
            })
        return {
            'skill': {'name': 'mango-monitoring-script-builder',
                      'resource': 'mango://skills/mango-monitoring-script-builder',
                      'entrypoint': 'SKILL.md'},
            'runtime': {'source': 'monitoring-service-heartbeat', 'freshness_seconds': 60,
                        'online_nodes': len(metadata_rows), 'unknown_nodes': unknown,
                        'python_versions': sorted({item.python_version for item in capabilities}),
                        'packages': packages, 'inventory_is_complete_package_list': False},
            'policy': {'auto_install_dependencies': False, 'save_starts_task': False,
                       'running_code_hot_reload': False, 'control_actions': ['start', 'stop']},
            'standard_library_examples': ['csv', 'json', 'time', 'datetime', 'urllib.request', 'pathlib'],
            'existing_dependency_alternatives': {'pandas_excel': 'openpyxl', 'pandas_csv': 'csv',
                                                 'http_request': 'requests / httpx / urllib.request'},
        }
