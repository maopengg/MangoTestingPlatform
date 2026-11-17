from copy import deepcopy
from hashlib import sha256
import json

from django.core.cache import cache
from django.core.exceptions import EmptyResultSet
from mangotools.enums import TestCaseTypeEnum

from src.apps.monitoring.selectors.execution_capacity import ExecutionCapacitySelector
from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.task_center.selectors.execution_efficiency import TaskEfficiencyOptionsSelector
from src.apps.test_center.schemas.execution_efficiency import ExecutionEfficiencyQuery
from src.apps.test_center.selectors.execution_efficiency import ExecutionEfficiencySelector
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionEfficiencyService:
    @staticmethod
    def options(user, **filters):
        all_products = PermissionMenuService.is_effective_super_admin(user) or ProjectProductScopeService.can_view_all_project_data(user)
        product_ids = None if all_products else ProjectProductScopeService.project_product_ids_for_user(user)
        return TaskEfficiencyOptionsSelector.options(product_ids=product_ids, **filters)

    @classmethod
    def query(cls, user, query: ExecutionEfficiencyQuery):
        # Recompute data scope before cache lookup, so revoked departments/guest settings take effect.
        reports = ExecutionEfficiencySelector.scoped_reports(user, query, historical=query.section == 'timing')
        try:
            sql, params = reports.query.sql_with_params()
        except EmptyResultSet:
            sql, params = 'empty', ()
        normalized = query.model_dump(mode='json', exclude={'page', 'page_size'})
        if query.section != 'timing':
            normalized.pop('start_at')
            normalized.pop('end_at')
            normalized['section'] = 'current'
        fingerprint = json.dumps([user.id, getattr(user, 'role_id', None), sql, params, normalized], default=str, sort_keys=True)
        key = 'execution-efficiency:v2:' + sha256(fingerprint.encode()).hexdigest()
        snapshot = cache.get(key)
        if snapshot is None:
            if query.section == 'timing':
                snapshot = ExecutionEfficiencySelector.historical(reports, query)
            else:
                workers = ExecutionCapacitySelector.api_workers()
                configured_capacity = max(1, workers['online']) * SystemConfigService.get_api_worker_thread_pool_size()
                timeouts = {
                    TestCaseTypeEnum.API.value: SystemConfigService.get_executor_execution_timeout_seconds(ExecutorTaskTypeEnum.API_EXECUTION.value, default_seconds=3600),
                    TestCaseTypeEnum.UI.value: SystemConfigService.get_executor_execution_timeout_seconds(ExecutorTaskTypeEnum.UI_CASE.value, default_seconds=3600),
                    TestCaseTypeEnum.PYTEST.value: SystemConfigService.get_executor_execution_timeout_seconds(ExecutorTaskTypeEnum.PYTEST_EXECUTION.value, default_seconds=3600),
                }
                snapshot = ExecutionEfficiencySelector.current(reports, query, workers, configured_capacity, timeouts)
            cache.set(key, snapshot, 60 if query.section == 'timing' else 10)
        snapshot = deepcopy(snapshot)
        if query.section != 'timing':
            items = snapshot.pop('anomalies') if query.section == 'anomalies' else snapshot.pop('items')
            snapshot.pop('items', None)
            snapshot.pop('anomalies', None)
            offset = (query.page - 1) * query.page_size
            snapshot.update(items=items[offset:offset + query.page_size], count=len(items),
                            page=query.page, page_size=query.page_size)
        return snapshot
