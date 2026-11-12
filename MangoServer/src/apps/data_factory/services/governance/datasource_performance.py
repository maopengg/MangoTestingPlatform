from collections import Counter

from src.apps.data_factory.models import Database
from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_POLICY_INVALID
from src.apps.data_factory.enums.performance import DatasourcePermitStateEnum
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.selectors.runtime_kv import RuntimeKVSelector


class DatasourcePerformanceService:
    @classmethod
    def settings_snapshot(cls):
        try:
            return {'runtime_status': cls.settings_status()}
        except DataFactoryError as error:
            if error.code != DATASOURCE_POLICY_INVALID.code:
                raise
            # 配置错误不能让修复配置的页面也无法打开；不伪造运行状态或静默放行执行。
            return {'runtime_status': [], 'performance_notice': error.msg}

    @staticmethod
    def settings_status():
        """仅供系统配置管理页读取；不返回来源明细、账号或凭据。"""
        groups = {}
        policy = DatasourceGovernorService.policy()
        for target in Database.objects.only('id', 'db_type', 'host', 'port').all():
            _, budget, group = DatasourceGovernorService.target_policy(target, policy)
            if group is not None:
                entry = groups.setdefault(group, {'group': group, 'connections': [],
                    'budget': budget.model_dump(mode='json'), 'counts': {}, 'connection_waiting': False,
                    'oldest_wait_seconds': 0, 'oldest_unknown_seconds': 0, 'admitted': 0, 'completed': 0})
                entry['connections'].append(target.id)
        rows = RuntimeKVSelector.entries(RuntimeKVNamespaceEnum.DATASOURCE_GOVERNOR.value,
                                         [f'group:{key}:control' for key in groups])
        now = DatasourceGovernorService.store().server_time().timestamp() if groups else 0
        for row in rows:
            group = row.key.split(':')[1]
            state = DatasourceGovernorService.read_state(row.value['data'])
            counts = Counter()
            for item in state.permits.values():
                counts[f'{item.kind.value}_{"suspect" if item.expires_at <= now else item.state.value}'] += item.slots
            unknown = [value for value in state.permits.values()
                       if value.state == DatasourcePermitStateEnum.SUSPECT or value.expires_at <= now]
            groups[group].update(counts=dict(counts), connection_waiting=state.connection_wait_until > now,
                                 oldest_wait_seconds=max(0, now - state.connection_wait_since)
                                     if state.connection_wait_until > now else 0,
                                 oldest_unknown_seconds=max([0, *(now - (value.unknown_since or value.expires_at)
                                                                 for value in unknown)]),
                                 admitted=state.admitted, completed=state.completed)
        return list(groups.values())
