from src.common.enums.base import BaseEnum


class DatasourceAuditSourceEnum(BaseEnum):
    CONNECTION = ('data_source_connection', '连接操作')
    METADATA = ('data_source_metadata', '元数据操作')
    RUNTIME = ('data_source_runtime', '运行时数据源操作')
    MCP = ('mcp', 'MCP调用')
    API_CASE_RESOURCE = ('api_case_resource', 'API创建资源清理')


class DatasourceAuditStageEnum(BaseEnum):
    EXTERNAL_CLEANUP = ('external_cleanup', '关联资源清理与回查')
    CONNECT = ('connect', '连接建立')
    NETWORK_PROBE = ('network_probe', '网络探测')
    TEST_CONNECTION = ('test_connection', '连接测试')
    STATEMENT = ('statement', '结构语句')
    REDIS_COMMAND = ('redis_command', 'Redis命令')
    ES_SEARCH = ('es_search', 'ES查询')
    DISCOVER_INDICES = ('discover_indices', '索引发现')
    GENERATED_KEY_LOOKUP = ('generated_key_lookup', '生成主键回读')
    NESTED_QUERY = ('nested_query', '关联查询')
    EXECUTE = ('execute', '执行')
    CONDITION_EXECUTE = ('condition_execute', '条件执行')
    QUERY = ('query', '查询')
    TRANSACTION = ('transaction', '事务提交与回滚')
