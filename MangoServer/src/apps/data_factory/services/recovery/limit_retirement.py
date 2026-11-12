"""一次性配置退役，不参与日常执行；不核销任何未知操作或物理连接。"""
import json

from django.db import transaction

from src.apps.data_factory.exceptions import DataFactoryError, DATASOURCE_LIMIT_RETIREMENT_BLOCKED
from src.apps.data_factory.schemas.performance import DatasourceGovernorState, DatasourcePerformancePolicy
from src.apps.system.enums import RuntimeServiceName
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.selectors.configuration import ConfigurationSelector
from src.apps.system.services.configuration.cache_data import CacheDataService
from src.apps.system.selectors.runtime_kv import RuntimeKVSelector
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.configuration.system_config import SystemConfigService


class DatasourceLimitRetirementService:
    @staticmethod
    def policy(value):
        if value.get('version') == 2:
            return DatasourcePerformancePolicy.model_validate(value, strict=True)
        if value.get('version', 1) != 1 or value.get('instances') or value.get('scopes'):
            raise DataFactoryError(DATASOURCE_LIMIT_RETIREMENT_BLOCKED, value=('请先核查旧实例覆盖和子配额，不能静默改变实例归属',))
        defaults = DatasourcePerformancePolicy().model_dump(mode='json')
        for kind in ('mysql', 'redis', 'elasticsearch'):
            if 'connections' in value.get(kind, {}):
                defaults[kind] = {'connections': value[kind]['connections']}
        for key in ('pool_size', 'pool_idle_seconds', 'max_local_pools',
                    'cleanup_completion_seconds', 'cleanup_consumer_threads'):
            if key in value:
                defaults[key] = value[key]
        if 'pool_size' not in value:
            defaults['pool_size'] = min(defaults['pool_size'],
                min(defaults[kind]['connections'] for kind in ('mysql', 'redis', 'elasticsearch')) - 1)
        return DatasourcePerformancePolicy.model_validate(defaults, strict=True)

    @staticmethod
    def state(value):
        if value.get('version', 1) not in (1, 2):
            raise DataFactoryError(DATASOURCE_LIMIT_RETIREMENT_BLOCKED, value=('运行态版本无法识别，未更改占用',))
        # 只删除退役的计数器和已停止进程的排队登记；保留完整 owner、审计、会话和时间证据。
        retired = {'tokens', 'normal_tokens', 'metadata_tokens', 'updated_at', 'waiters', 'throttled', 'scopes'}
        result = {key: item for key, item in value.items() if key not in retired}
        if value.get('version', 1) == 1 and isinstance(result.get('permits'), dict):
            permits = {}
            for owner, permit in result['permits'].items():
                if isinstance(permit, dict) and 'scopes' in permit:
                    # 旧版在单项占用中也保存空子配额；非空配置仍需人工核对，不能丢失归属证据。
                    if not isinstance(permit['scopes'], list) or permit['scopes']:
                        raise DataFactoryError(DATASOURCE_LIMIT_RETIREMENT_BLOCKED,
                            value=('历史占用含非空或格式异常的子配额，请先核查；未更改占用',))
                    permit = {key: item for key, item in permit.items() if key != 'scopes'}
                permits[owner] = permit
            result['permits'] = permits
        result['version'] = 2
        return DatasourceGovernorState.model_validate(result).model_dump(mode='json')

    @classmethod
    @transaction.atomic
    def run(cls, *, apply=False):
        config = ConfigurationSelector.locked_datasource_policy()
        old = SystemConfigService.cast_value(config.value, config.value_type, {})
        policy = cls.policy(old)
        services = (RuntimeServiceName.CORE_API, RuntimeServiceName.API_WORKER,
                    RuntimeServiceName.MCP, RuntimeServiceName.SCHEDULER, RuntimeServiceName.MONITORING)
        online = [service.value for service in services if ServiceHeartbeatService.get_online_instances(service)]
        if apply and online:
            raise DataFactoryError(DATASOURCE_LIMIT_RETIREMENT_BLOCKED,
                value=('必须先排空并停止旧版数据源调用进程，再等待心跳离线；禁止新旧版本混跑',))
        store = RuntimeKV.namespace(RuntimeKVNamespaceEnum.DATASOURCE_GOVERNOR)
        rows = list(RuntimeKVSelector.active(store.name).filter(
            key__startswith='group:', key__endswith=':control').select_for_update())
        prepared = []
        for row in rows:
            original = row.value['data']
            state = cls.state(original)
            reserve = max(policy.mysql.connections, policy.redis.connections, policy.elasticsearch.connections) * 700
            if len(json.dumps({'data': state}).encode()) + reserve > store.policy['max_bytes']:
                raise DataFactoryError(DATASOURCE_LIMIT_RETIREMENT_BLOCKED,
                    value=('历史占用证据过多，请先逐项核查结算，不能丢弃证据以腾出连接记录空间',))
            prepared.append((row.key, original, state))
        if apply:
            store.set_if_absent('retired:policy:v1', old, ttl=None)
            for key, original, state in prepared:
                store.set_if_absent(f'retired:{key}', original, ttl=None)
                store.atomic_update(key, lambda value, now, expected=original, replacement=state:
                    cls.replace_state(value, expected, replacement), ttl=None)
            CacheDataService.replace_retired_datasource_policy(config, policy.model_dump(mode='json'))
        return {'applied': apply, 'online_services': online,
                'instance_groups': len(prepared), 'policy': policy.model_dump(mode='json'),
                'preserved_permits': sum(len(state['permits']) for _, _, state in prepared)}

    @staticmethod
    def replace_state(value, expected, replacement):
        if value != expected:
            raise DataFactoryError(DATASOURCE_LIMIT_RETIREMENT_BLOCKED,
                value=('占用快照在退役期间发生变化，未覆盖新状态，请重新核查',))
        return replacement, None
