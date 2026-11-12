import base64
import json
import shlex
import socket
import ssl
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from src.apps.data_factory.exceptions import (
    DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED,
    DATA_SOURCE_DATABASE_PERMISSION_READ_BINDING_INVALID,
    DATA_SOURCE_INVALID,
    DATA_SOURCE_EXECUTION_NOT_ALLOWED,
    DATA_SOURCE_NAME_INVALID,
    DATA_SOURCE_JSON_INVALID,
    DATA_SOURCE_FAILED,
    DATA_SOURCE_FAILED_CODE_FAILED,
    DATA_SOURCE_INVALID_CODE_INVALID,
    DATA_SOURCE_DATA_SOURCE_PERMISSION_WRITE_BINDING_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import Database
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.protocols.elasticsearch_http import open_elasticsearch_request
from src.apps.data_factory.services.sql.sql_query import DataFactorySqlQuery
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.services.datasource.data_source import DataSourceConnectionService


class DataFactoryDatasourceQuery:
    """按真实数据库类型执行受限的只读查询。"""

    MAX_INPUT_LENGTH = 100_000

    @classmethod
    def max_rows(cls) -> int:
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get_ranged_int('DATA_QUERY_MAX_ROWS')

    REDIS_READ_COMMANDS = {
        'EXISTS', 'GET', 'GETRANGE', 'HEXISTS', 'HGET', 'HGETALL', 'HKEYS', 'HLEN',
        'HMGET', 'HSCAN', 'HSTRLEN', 'HVALS', 'LLEN', 'LINDEX', 'LRANGE', 'MGET',
        'PTTL', 'SCAN', 'SCARD', 'SISMEMBER', 'SMEMBERS', 'SRANDMEMBER', 'STRLEN',
        'TTL', 'TYPE', 'ZCARD', 'ZCOUNT', 'ZRANGE', 'ZRANK', 'ZREVRANGE', 'ZREVRANK',
        'ZSCAN', 'ZSCORE',
    }
    REDIS_BLOCKED_COMMANDS = {
        'ACL', 'CONFIG', 'DEBUG', 'EVAL', 'EVALSHA', 'FLUSHALL', 'FLUSHDB',
        'FUNCTION', 'MODULE', 'SCRIPT', 'SHUTDOWN',
    }

    @classmethod
    def redis_command_name(cls, command: str) -> str:
        command = (command or '').strip()
        if not command:
            raise DataFactoryError(DATA_SOURCE_INVALID)
        if len(command) > cls.MAX_INPUT_LENGTH:
            raise DataFactoryError(DATA_SOURCE_FAILED, value=('命令内容过长',))
        try:
            parts = shlex.split(command)
        except ValueError as error:
            raise DataFactoryError(DATA_SOURCE_INVALID_CODE_INVALID, value=(str(error),)) from error
        if not parts:
            raise DataFactoryError(DATA_SOURCE_INVALID)
        return parts[0].upper()

    @classmethod
    def query(cls, database: Database, payload: dict, allow_query: bool = False) -> dict:
        if not allow_query:
            raise DataFactoryError(DATA_SOURCE_DATABASE_PERMISSION_READ_BINDING_INVALID)
        if database.source_category == DataSourceCategoryEnum.DATABASE.value:
            return DataFactorySqlQuery.query(
                database,
                payload.get('sql') or payload.get('statement') or '',
                limit=cls.max_rows(),
                allow_query=True,
            )
        if database.db_type == DataSourceTypeEnum.REDIS.value:
            return cls.query_redis(database, payload.get('command') or payload.get('statement') or '')
        if database.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            return cls.query_elasticsearch(database, payload.get('index'), payload.get('query'))
        type_name = DataSourceTypeEnum.obj().get(database.db_type, database.db_type)
        raise DataFactoryError(DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED, value=(type_name,))

    @classmethod
    def query_redis(cls, database: Database, command: str) -> dict:
        command_name = cls.redis_command_name(command)
        if command_name not in cls.REDIS_READ_COMMANDS:
            raise DataFactoryError(DATA_SOURCE_EXECUTION_NOT_ALLOWED, value=(command_name,))
        return cls.execute_redis(
            database,
            command,
            allow_query=True,
            allow_write=False,
        )

    @classmethod
    def execute_redis(
            cls,
            database: Database,
            command: str,
            *,
            allow_query: bool,
            allow_write: bool,
    ) -> dict:
        command = (command or '').strip()
        if not command:
            raise DataFactoryError(DATA_SOURCE_INVALID)
        if len(command) > cls.MAX_INPUT_LENGTH:
            raise DataFactoryError(DATA_SOURCE_FAILED, value=('命令内容过长',))
        try:
            parts = shlex.split(command)
        except ValueError as error:
            raise DataFactoryError(DATA_SOURCE_INVALID_CODE_INVALID, value=(str(error),)) from error
        if not parts:
            raise DataFactoryError(DATA_SOURCE_INVALID)
        command_name = parts[0].upper()
        if command_name in cls.REDIS_BLOCKED_COMMANDS:
            raise DataFactoryError(DATA_SOURCE_EXECUTION_NOT_ALLOWED, value=(command_name,))
        from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
        DatasourceCostService.redis(parts)
        is_query = command_name in cls.REDIS_READ_COMMANDS
        if is_query and not allow_query:
            raise DataFactoryError(DATA_SOURCE_DATABASE_PERMISSION_READ_BINDING_INVALID)
        if not is_query and not allow_write:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_PERMISSION_WRITE_BINDING_INVALID)

        return cls._execute_redis(database, command, parts, is_query)

    @classmethod
    @SqlExecutionAuditService.audited(DatasourceAuditStageEnum.REDIS_COMMAND.value)
    def _execute_redis(cls, database, command, parts, is_query):
        import redis
        from src.apps.data_factory.services.pool.protocol_pool import ProtocolPoolRegistry
        from src.apps.data_factory.services.protocols.redis_protocol import BoundedRedisParser

        command_name = parts[0].upper()
        options = database.extra_config or {}

        def factory(size):
            pool_class = redis.SSLConnection if options.get('ssl') else redis.Connection
            pool = redis.BlockingConnectionPool(
                connection_class=pool_class, max_connections=size, timeout=DataSourceConnectionService.timeout_seconds(),
                host=database.host, port=int(database.port), username=database.user or None,
                password=database.password or None, db=database.redis_db or 0, decode_responses=True,
                encoding_errors='replace',
                socket_timeout=DataSourceConnectionService.timeout_seconds(),
                socket_connect_timeout=DataSourceConnectionService.timeout_seconds(),
                retry_on_timeout=False,
                parser_class=BoundedRedisParser,
            )
            return redis.Redis.from_pool(pool)

        try:
            with ProtocolPoolRegistry.borrow(database, 'redis', factory) as client:
                # 使用维护中的客户端传输，但保留原 RESP 结果形状，不能把 SET 的 OK
                # 静默改成 True、或将 HSCAN 的数组改成字典而改变 Case 断言。
                pool = client.connection_pool
                from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing
                from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
                with Timing.measure(Phase.CONNECT):
                    connection = pool.get_connection()
                try:
                    with Timing.measure(Phase.EXECUTE):
                        connection.send_command(*parts)
                    with Timing.measure(Phase.FETCH):
                        result = connection.read_response()
                except BaseException:
                    connection.disconnect()
                    raise
                finally:
                    pool.release(connection)
            return {
                'type': 'redis',
                'database': database.redis_db or 0,
                'command': command_name,
                'execution_type': 'query' if is_query else 'write',
                'result': result,
            }
        except Exception as error:
            if isinstance(error, DataFactoryError):
                raise
            DataSourceErrorService.raise_redis_error(database, error)

    @classmethod
    def query_elasticsearch(cls, database: Database, index: str, query) -> dict:
        index = (index or '').strip()
        if not index or '/' in index or '\\' in index or '..' in index:
            raise DataFactoryError(DATA_SOURCE_NAME_INVALID)
        if isinstance(query, str):
            try:
                query = json.loads(query)
            except json.JSONDecodeError as error:
                raise DataFactoryError(DATA_SOURCE_JSON_INVALID) from error
        if not isinstance(query, dict):
            raise DataFactoryError(DATA_SOURCE_JSON_INVALID)

        from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
        DatasourceCostService.elasticsearch(index, query)

        return cls._query_elasticsearch(database, index, query)

    @classmethod
    @SqlExecutionAuditService.audited(DatasourceAuditStageEnum.ES_SEARCH.value)
    def _query_elasticsearch(cls, database, index, query):
        from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
        body = dict(query)
        try:
            requested_size = int(body.get('size', 20))
        except (TypeError, ValueError):
            from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
            DatasourceCostService.reject('ES分页参数 size 必须为整数。请修改用例查询配置', not_sent=True)
        maximum = cls.max_rows()
        if requested_size > maximum:
            from src.apps.data_factory.services.governance.datasource_cost import DatasourceCostService
            DatasourceCostService.reject(f'ES查询条数超过返回上限：当前配置最多 {maximum} 条，查询size为 {requested_size}。请修改用例的size或查询范围；本次未发送查询', not_sent=True)
        body['size'] = requested_size
        encoded_body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        if len(encoded_body) > cls.MAX_INPUT_LENGTH:
            DatasourceCostService.reject(f'ES查询请求过大：最多允许 {cls.MAX_INPUT_LENGTH} 字节，当前为 {len(encoded_body)} 字节。请检查用例是否拼接了过多查询条件；本次未发送查询', not_sent=True)

        options = database.extra_config or {}
        scheme = options.get('scheme', 'http')
        path_prefix = str(options.get('path_prefix', '') or '').strip('/')
        base_url = f'{scheme}://{database.host}:{database.port}'
        if path_prefix:
            base_url = f'{base_url}/{path_prefix}'
        safe_index = urllib_parse.quote(index, safe='*,-_.')
        url = f'{base_url}/{safe_index}/_search'
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if database.user or database.password:
            credential = base64.b64encode(
                f'{database.user}:{database.password}'.encode('utf-8')
            ).decode('ascii')
            headers['Authorization'] = f'Basic {credential}'
        context = None
        if scheme == 'https' and options.get('verify_certs', True) is False:
            context = ssl._create_unverified_context()
        request_timeout = DataSourceConnectionService.timeout_seconds()
        try:
            request = urllib_request.Request(url, data=encoded_body, headers=headers, method='POST')
            with open_elasticsearch_request(
                    request,
                    timeout=request_timeout,
                    target=database,
                    context=context,
            ) as response:
                body = response.read(1_048_577)
                if len(body) > 1_048_576:
                    DatasourceCostService.reject(f'ES返回结果超过大小上限：最多允许 1048576 字节，已读取至少 {len(body)} 字节。请减少查询字段或缩小查询范围；本次不返回截断结果')
                result = json.loads(body.decode('utf-8'))
                if isinstance(result, dict) and (result.get('timed_out') or (result.get('_shards') or {}).get('failed', 0)):
                    reasons = []
                    if result.get('timed_out'):
                        reasons.append('ES返回timed_out=true')
                    if (result.get('_shards') or {}).get('failed', 0):
                        reasons.append(f"失败分片数为 {(result.get('_shards') or {})['failed']}")
                    raise DataFactoryError(DATA_SOURCE_FAILED_CODE_FAILED, value=(
                        'ES查询结果不完整：' + '，'.join(reasons) + '。不能据此判断数据不存在，请检查ES查询耗时和分片状态',))
            return {
                'type': 'elasticsearch',
                'index': index,
                'result': result,
            }
        except urllib_error.HTTPError as error:
            DataSourceErrorService.raise_elasticsearch_http_error(database, error)
        except (urllib_error.URLError, TimeoutError, ValueError, OSError) as error:
            DataSourceErrorService.raise_elasticsearch_transport_error(database, error, timeout=request_timeout)
