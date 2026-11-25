from src.common.enums.base import BaseEnum


class RuntimeKVNamespaceEnum(BaseEnum):
    DATASOURCE_GOVERNOR = ('datasource_governor', '数据源并发与连接配额')
    API_AUTH = ('api_auth', 'API 授权运行数据')
    PERF_SUBSCRIPTION = ('perf_subscription', '性能实时订阅')
    REQUEST_DEDUP = ('request_dedup', '请求去重')
    EXECUTOR_STATE = ('executor_state', '执行器连接临时状态')
    ACTUATOR_CONFIG = ('actuator_config', '执行器配置请求结果')
    MCP_CONFIRMATION = ('mcp_confirmation', 'MCP 危险操作确认')
    EXECUTION_SEARCH = ('execution_search', '执行内容检索任务')


class RuntimeKVValueTypeEnum(BaseEnum):
    JSON = (0, 'JSON 数据')
    COUNTER = (1, '整数计数器')
