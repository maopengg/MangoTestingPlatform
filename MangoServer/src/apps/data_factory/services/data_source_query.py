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
from src.apps.data_factory.services.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.elasticsearch_http import open_elasticsearch_request
from src.apps.data_factory.services.sql_query import DataFactorySqlQuery
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.services.data_source import DataSourceConnectionService


class DataFactoryDatasourceQuery:
    """按真实数据库类型执行受限的只读查询。"""

    MAX_INPUT_LENGTH = 100_000

    @classmethod
    def max_rows(cls) -> int:
        from src.apps.system.services.system_config import SystemConfigService

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
        is_query = command_name in cls.REDIS_READ_COMMANDS
        if is_query and not allow_query:
            raise DataFactoryError(DATA_SOURCE_DATABASE_PERMISSION_READ_BINDING_INVALID)
        if not is_query and not allow_write:
            raise DataFactoryError(DATA_SOURCE_DATA_SOURCE_PERMISSION_WRITE_BINDING_INVALID)

        raw_socket = None
        connection = None
        try:
            raw_socket = socket.create_connection(
                (database.host, int(database.port)),
                timeout=DataSourceConnectionService.timeout_seconds(),
            )
            raw_socket.settimeout(DataSourceConnectionService.timeout_seconds())
            options = database.extra_config or {}
            if options.get('ssl'):
                context = ssl.create_default_context()
                raw_socket = context.wrap_socket(raw_socket, server_hostname=database.host)
            connection = raw_socket.makefile('rwb')
            if database.password:
                auth_parts = ['AUTH']
                if database.user:
                    auth_parts.append(database.user)
                auth_parts.append(database.password)
                DataSourceConnectionService._redis_command(connection, *auth_parts)
            database_index = database.redis_db
            if database_index:
                DataSourceConnectionService._redis_command(connection, 'SELECT', str(database_index))
            result = DataSourceConnectionService._redis_command(connection, *parts)
            return {
                'type': 'redis',
                'database': database_index,
                'command': command_name,
                'execution_type': 'query' if is_query else 'write',
                'result': result,
            }
        except Exception as error:
            if isinstance(error, DataFactoryError):
                raise
            DataSourceErrorService.raise_redis_error(database, error)
        finally:
            if connection:
                connection.close()
            if raw_socket:
                raw_socket.close()

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

        body = dict(query)
        try:
            requested_size = int(body.get('size', 20))
        except (TypeError, ValueError):
            requested_size = 20
        body['size'] = max(0, min(requested_size, cls.max_rows()))
        encoded_body = json.dumps(body, ensure_ascii=False).encode('utf-8')
        if len(encoded_body) > cls.MAX_INPUT_LENGTH:
            raise DataFactoryError(DATA_SOURCE_FAILED_CODE_FAILED, value=('查询条件内容过长',))

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
        try:
            request = urllib_request.Request(url, data=encoded_body, headers=headers, method='POST')
            with open_elasticsearch_request(
                    request,
                    timeout=DataSourceConnectionService.timeout_seconds(),
                    context=context,
            ) as response:
                result = json.loads(response.read().decode('utf-8'))
            return {
                'type': 'elasticsearch',
                'index': index,
                'result': result,
            }
        except urllib_error.HTTPError as error:
            DataSourceErrorService.raise_elasticsearch_http_error(database, error)
        except (urllib_error.URLError, TimeoutError, ValueError, OSError) as error:
            DataSourceErrorService.raise_elasticsearch_transport_error(database, error)
