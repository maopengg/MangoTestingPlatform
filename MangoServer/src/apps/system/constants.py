SNOWFLAKE_SEQUENCE_KEY = '__system_snowflake_next_tick__'
EVALUATION_DEFAULT_AI_PROFILE_ID = '__system_default__'

# namespace 策略；业务配置与历史数据不随策略注册自动迁移。
RUNTIME_KV_POLICIES = {
    'datasource_governor': {'ttl': None, 'persistent': True, 'sensitive': False, 'max_bytes': 131072},
    'api_auth': {'ttl': 3600, 'persistent': True, 'sensitive': True, 'max_bytes': 65536},
    'perf_subscription': {'ttl': 120, 'persistent': False, 'sensitive': False, 'max_bytes': 65536},
    'request_dedup': {'ttl': 300, 'persistent': False, 'sensitive': False, 'max_bytes': 65536},
    'executor_state': {'ttl': 90, 'persistent': False, 'sensitive': False, 'max_bytes': 65536},
    'actuator_config': {'ttl': 60, 'persistent': False, 'sensitive': True, 'max_bytes': 65536},
    'mcp_confirmation': {'ttl': 600, 'persistent': False, 'sensitive': True, 'max_bytes': 8192},
}
