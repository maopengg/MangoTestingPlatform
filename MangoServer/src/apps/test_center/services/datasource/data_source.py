# -*- coding: utf-8 -*-
import base64
import json
import socket
import ssl
from urllib import error as urllib_error
from urllib import request as urllib_request

from src.apps.data_factory.exceptions import (
    DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED,
    DATA_SOURCE_SQL_DATABASE_UNSUPPORTED,
)
from src.apps.data_factory.models import Database
from src.apps.data_factory.schemas.datasource_target import DatasourceTarget
from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.protocols.elasticsearch_http import open_elasticsearch_request
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.exceptions import (
    TEST_DATA_SOURCE_REDIS_ARRAY_TOO_LARGE,
    TEST_DATA_SOURCE_REDIS_EMPTY,
    TEST_DATA_SOURCE_REDIS_ERROR,
    TEST_DATA_SOURCE_REDIS_ITEM_TOO_LARGE,
    TEST_DATA_SOURCE_REDIS_ITEMS_EXCEEDED,
    TEST_DATA_SOURCE_REDIS_PING_INVALID,
    TEST_DATA_SOURCE_REDIS_RESPONSE_INVALID,
    TestCenterError,
)


class DataSourceConnectionService:
    """全局数据库连接能力入口。具体协议由类型适配器负责。"""

    @classmethod
    def timeout_seconds(cls) -> int:
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get_ranged_int('DATA_SOURCE_TIMEOUT_SECONDS')

    @classmethod
    def redis_max_response_items(cls) -> int:
        from src.apps.system.services.configuration.system_config import SystemConfigService

        return SystemConfigService.get_ranged_int('REDIS_MAX_RESPONSE_ITEMS')

    REDIS_MAX_BULK_BYTES = 1_048_576

    @classmethod
    def diagnose_connection(cls, data_source: Database | DatasourceTarget) -> dict:
        checks = []
        network_check = cls._diagnose_network(data_source)
        checks.append(network_check)
        if network_check['status'] == 'failed':
            checks.extend([
                cls._diagnostic_check('authentication', '账号、密码及连接配置', 'skipped', '网络不可达，未执行'),
                cls._diagnostic_check('target', cls._target_check_name(data_source), 'skipped', '网络不可达，未执行'),
            ])
            return cls._diagnostic_result(data_source, checks, network_check['message'])

        try:
            if not isinstance(data_source, DatasourceTarget):
                data_source = DatasourceTargetService.maintenance(data_source)
            result = cls.test_connection(data_source)
        except Exception as error:
            message = error.msg if isinstance(error, TestCenterError) else cls._safe_error(data_source, error)
            failure_stage = cls._connection_failure_stage(message)
            if failure_stage == 'target':
                checks.append(cls._diagnostic_check(
                    'authentication', '账号、密码及连接配置', 'passed', '服务端已接受连接配置',
                ))
                checks.append(cls._diagnostic_check(
                    'target', cls._target_check_name(data_source), 'failed', message,
                ))
            else:
                checks.append(cls._diagnostic_check(
                    'authentication', '账号、密码及连接配置', 'failed', message,
                ))
                checks.append(cls._diagnostic_check(
                    'target', cls._target_check_name(data_source), 'skipped', '认证或连接配置失败，未执行',
                ))
            return cls._diagnostic_result(data_source, checks, message)

        checks.extend([
            cls._diagnostic_check(
                'authentication', '账号、密码及连接配置', 'passed', '认证及协议配置正确',
            ),
            cls._diagnostic_check(
                'target', cls._target_check_name(data_source), 'passed', cls._target_success_message(data_source),
            ),
        ])
        return {**result, 'connected': True, 'checks': checks, 'error': None}

    @classmethod
    @SqlExecutionAuditService.audited(DatasourceAuditStageEnum.NETWORK_PROBE.value)
    def _diagnose_network(cls, data_source: Database) -> dict:
        if data_source.db_type == DataSourceTypeEnum.SQLITE.value:
            return cls._diagnostic_check('network', '域名解析与端口访问', 'passed', 'SQLite为本地文件，无需网络连接')
        host = str(data_source.host or '').strip()
        port = data_source.port
        if not host or not port:
            return cls._diagnostic_check('network', '域名解析与端口访问', 'failed', '域名/IP或端口未配置')
        try:
            addresses = socket.getaddrinfo(host, int(port), type=socket.SOCK_STREAM)
            resolved_ips = sorted({item[4][0] for item in addresses})
            with socket.create_connection((host, int(port)), timeout=cls.timeout_seconds()):
                pass
            resolved = ', '.join(resolved_ips[:3]) or host
            return cls._diagnostic_check(
                'network', '域名解析与端口访问', 'passed', f'{host}:{port} 可访问，解析地址：{resolved}',
            )
        except socket.gaierror as error:
            return cls._diagnostic_check(
                'network', '域名解析与端口访问', 'failed', f'域名解析失败：{error}',
            )
        except (OSError, TimeoutError) as error:
            return cls._diagnostic_check(
                'network', '域名解析与端口访问', 'failed', f'{host}:{port} 无法访问：{error}',
            )

    @staticmethod
    def _diagnostic_check(key: str, name: str, status: str, message: str) -> dict:
        return {'key': key, 'name': name, 'status': status, 'message': message}

    @classmethod
    def _diagnostic_result(cls, data_source, checks: list[dict], error: str) -> dict:
        return {
            'data_source_id': data_source.id,
            'source_category': data_source.source_category,
            'source_type': data_source.db_type,
            'name': cls.connection_name(data_source),
            'alias': data_source.display_name or '',
            'display_name': cls.display_label(data_source),
            'host': data_source.host,
            'port': data_source.port,
            'connected': False,
            'checks': checks,
            'error': cls._safe_error(data_source, Exception(error)),
            'details': {},
        }

    @staticmethod
    def _connection_failure_stage(message: str) -> str:
        normalized = str(message or '').lower()
        target_markers = (
            'unknown database', 'database does not exist', 'does not exist',
            'invalid catalog', 'cannot open database', 'select index is out of range',
        )
        return 'target' if any(marker in normalized for marker in target_markers) else 'authentication'

    @staticmethod
    def _target_check_name(data_source: Database) -> str:
        if data_source.db_type == DataSourceTypeEnum.REDIS.value:
            return 'Redis DB配置'
        if data_source.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            return 'Elasticsearch集群配置'
        return '目标数据库配置'

    @staticmethod
    def _target_success_message(data_source: Database) -> str:
        if data_source.db_type == DataSourceTypeEnum.REDIS.value:
            database_index = data_source.redis_db
            return f'Redis DB {database_index} 可正常访问'
        if data_source.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            return 'Elasticsearch集群可正常访问'
        return '连接可正常执行SELECT 1；业务库权限以环境绑定诊断为准'

    @classmethod
    @SqlExecutionAuditService.audited(DatasourceAuditStageEnum.TEST_CONNECTION.value)
    def test_connection(cls, data_source: Database) -> dict:
        if not isinstance(data_source, DatasourceTarget):
            data_source = DatasourceTargetService.maintenance(data_source)
        if data_source.source_category == DataSourceCategoryEnum.DATABASE.value:
            from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource

            result = DataFactoryDatasource.test_connection(data_source)
            return cls._result(data_source, {"database": result})
        if data_source.db_type == DataSourceTypeEnum.REDIS.value:
            return cls._result(data_source, cls._test_redis(data_source))
        if data_source.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            return cls._result(data_source, cls._test_elasticsearch(data_source))
        raise TestCenterError(DATA_SOURCE_DATABASE_TYPE_UNSUPPORTED, value=(data_source.db_type,))

    @classmethod
    def require_sql(cls, data_source: Database) -> None:
        if data_source.source_category != DataSourceCategoryEnum.DATABASE.value:
            type_name = DataSourceTypeEnum.obj().get(data_source.db_type, data_source.db_type)
            raise TestCenterError(DATA_SOURCE_SQL_DATABASE_UNSUPPORTED, value=(type_name,))

    @staticmethod
    def capabilities(data_source: Database) -> dict:
        return {
            "sql": data_source.source_category == DataSourceCategoryEnum.DATABASE.value,
            "key_value": data_source.db_type == DataSourceTypeEnum.REDIS.value,
            "search": data_source.db_type == DataSourceTypeEnum.ELASTICSEARCH.value,
        }

    @staticmethod
    def connection_name(data_source: Database) -> str:
        if data_source.source_category == DataSourceCategoryEnum.DATABASE.value:
            return data_source.display_name
        if data_source.db_type == DataSourceTypeEnum.REDIS.value:
            return f"{data_source.host}:{data_source.port}"
        if data_source.db_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            path_prefix = str((data_source.extra_config or {}).get("path_prefix", "") or "").strip("/")
            suffix = f"/{path_prefix}" if path_prefix else ""
            return f"{data_source.host}:{data_source.port}{suffix}"
        return data_source.display_name or f"{data_source.host}:{data_source.port}"

    @classmethod
    def display_label(cls, data_source: Database) -> str:
        return data_source.display_name or cls.connection_name(data_source)

    @classmethod
    def _result(cls, data_source: Database, details: dict) -> dict:
        return {
            "data_source_id": data_source.id,
            "source_category": data_source.source_category,
            "source_type": data_source.db_type,
            "name": cls.connection_name(data_source),
            "alias": data_source.display_name or "",
            "display_name": cls.display_label(data_source),
            "host": data_source.host,
            "port": data_source.port,
            "connected": True,
            "capabilities": cls.capabilities(data_source),
            "details": details,
        }

    @classmethod
    def _test_redis(cls, data_source: Database) -> dict:
        options = data_source.extra_config or {}
        raw_socket = None
        connection = None
        try:
            raw_socket = socket.create_connection(
                (data_source.host, int(data_source.port)),
                timeout=cls.timeout_seconds(),
            )
            raw_socket.settimeout(cls.timeout_seconds())
            if options.get("ssl"):
                context = ssl.create_default_context()
                raw_socket = context.wrap_socket(raw_socket, server_hostname=data_source.host)
            connection = raw_socket.makefile("rwb")
            if data_source.password:
                auth_parts = ["AUTH"]
                if data_source.user:
                    auth_parts.append(data_source.user)
                auth_parts.append(data_source.password)
                cls._redis_command(connection, *auth_parts)
            database_index = data_source.redis_db
            if database_index:
                cls._redis_command(connection, "SELECT", str(database_index))
            pong = cls._redis_command(connection, "PING")
            if str(pong).upper() != "PONG":
                raise TestCenterError(TEST_DATA_SOURCE_REDIS_PING_INVALID, value=(pong,))
            return {
                "protocol": "rediss" if options.get("ssl") else "redis",
                "database": database_index,
                "ping": "PONG",
            }
        except Exception as exc:
            if isinstance(exc, TestCenterError):
                raise
            DataSourceErrorService.raise_redis_error(data_source, exc)
        finally:
            if connection:
                connection.close()
            if raw_socket:
                raw_socket.close()

    @classmethod
    def _redis_command(cls, connection, *parts: str):
        payload = f"*{len(parts)}\r\n".encode()
        for part in parts:
            value = str(part).encode("utf-8")
            payload += f"${len(value)}\r\n".encode() + value + b"\r\n"
        connection.write(payload)
        connection.flush()
        return cls._read_redis_response(connection)

    @classmethod
    def _read_redis_response(cls, connection, budget=None):
        budget = budget or {"items": 0}
        budget["items"] += 1
        if budget["items"] > cls.redis_max_response_items():
            raise TestCenterError(TEST_DATA_SOURCE_REDIS_ITEMS_EXCEEDED)
        marker = connection.read(1)
        if not marker:
            raise TestCenterError(TEST_DATA_SOURCE_REDIS_EMPTY)
        line = connection.readline().rstrip(b"\r\n")
        if marker == b"+":
            return line.decode("utf-8", errors="replace")
        if marker == b":":
            return int(line)
        if marker == b"-":
            raise TestCenterError(
                TEST_DATA_SOURCE_REDIS_ERROR,
                value=(line.decode("utf-8", errors="replace"),),
            )
        if marker == b"$":
            length = int(line)
            if length < 0:
                return None
            if length > cls.REDIS_MAX_BULK_BYTES:
                raise TestCenterError(TEST_DATA_SOURCE_REDIS_ITEM_TOO_LARGE)
            value = connection.read(length)
            connection.read(2)
            return value.decode("utf-8", errors="replace")
        if marker == b"*":
            length = int(line)
            if length < 0:
                return None
            if length > cls.redis_max_response_items():
                raise TestCenterError(TEST_DATA_SOURCE_REDIS_ARRAY_TOO_LARGE)
            return [cls._read_redis_response(connection, budget) for _ in range(length)]
        raise TestCenterError(TEST_DATA_SOURCE_REDIS_RESPONSE_INVALID)

    @classmethod
    def _test_elasticsearch(cls, data_source: Database) -> dict:
        options = data_source.extra_config or {}
        scheme = options.get("scheme", "http")
        path_prefix = str(options.get("path_prefix", "") or "").strip("/")
        base_url = f"{scheme}://{data_source.host}:{data_source.port}"
        if path_prefix:
            base_url = f"{base_url}/{path_prefix}"
        url = f"{base_url}/_cluster/health?local=true"
        headers = {"Accept": "application/json"}
        if data_source.user or data_source.password:
            credential = base64.b64encode(
                f"{data_source.user}:{data_source.password}".encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = f"Basic {credential}"
        context = None
        if scheme == "https" and options.get("verify_certs", True) is False:
            context = ssl._create_unverified_context()
        try:
            req = urllib_request.Request(url, headers=headers, method="GET")
            with open_elasticsearch_request(req, timeout=cls.timeout_seconds(), target=data_source, context=context) as response:
                body = json.loads(response.read().decode("utf-8"))
            return {
                "protocol": scheme,
                "cluster_name": body.get("cluster_name"),
                "status": body.get("status"),
                "number_of_nodes": body.get("number_of_nodes"),
                "number_of_data_nodes": body.get("number_of_data_nodes"),
            }
        except urllib_error.HTTPError as exc:
            DataSourceErrorService.raise_elasticsearch_http_error(data_source, exc)
        except (urllib_error.URLError, TimeoutError, ValueError, OSError) as exc:
            DataSourceErrorService.raise_elasticsearch_transport_error(data_source, exc)

    @staticmethod
    def _safe_error(data_source: Database, error: Exception) -> str:
        message = str(error)
        if data_source.password:
            message = message.replace(data_source.password, "******")
        return message
