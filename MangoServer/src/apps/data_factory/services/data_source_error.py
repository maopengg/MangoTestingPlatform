import json
import socket
import ssl
from urllib import error as urllib_error

from src.apps.data_factory.exceptions import (
    DATA_SOURCE_FAILED,
    DATA_SOURCE_FAILED_CODE_FAILED,
    DATA_SOURCE_SQL_DATABASE_INVALID,
    DATA_SOURCE_SQL_PARAMETER_INVALID,
    DATA_SOURCE_SQL_DATABASE_INVALID_CODE_SQL_DATABASE_INVALID,
    DATA_SOURCE_SQL_EXECUTION_FAILED,
    DATA_SOURCE_SQL_EXECUTION_TIMEOUT,
    DATA_SOURCE_PERMISSION_FAILED,
    DATA_SOURCE_PARAMETER_INVALID,
    DATA_SOURCE_TYPE_INVALID,
    DATA_SOURCE_WRITE_NOT_ALLOWED,
    DATA_SOURCE_REDIS_NETWORK_FAILED,
    DATA_SOURCE_ELASTICSEARCH_QUERY_INVALID,
    DATA_SOURCE_ELASTICSEARCH_AUTHENTICATION_FAILED,
    DATA_SOURCE_PERMISSION_FAILED_CODE_PERMISSION_FAILED,
    DATA_SOURCE_NOT_FOUND,
    DATA_SOURCE_REQUEST_SERVICE_INVALID,
    DATA_SOURCE_JSON_PARSE_INVALID,
    DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED,
    DATA_SOURCE_REQUEST_FAILED,
    DataFactoryError,
)
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class DataSourceErrorService:
    """把不同驱动和协议的错误统一转成可直接展示的业务错误。"""

    @staticmethod
    def safe_detail(database, error: Exception) -> str:
        original = getattr(error, 'orig', None)
        detail = str(original or error).strip() or error.__class__.__name__
        password = getattr(database, 'password', None)
        if password:
            detail = detail.replace(str(password), '******')
        return detail

    @classmethod
    def raise_sql_error(cls, database, error: Exception) -> None:
        from sqlalchemy import exc as sqlalchemy_error

        type_name = DataSourceTypeEnum.obj().get(database.db_type, database.db_type)
        detail = cls.safe_detail(database, error)
        normalized = detail.lower()
        if database.db_type == DataSourceTypeEnum.MYSQL.value and not database.database_name and 'no database selected' in normalized:
            from src.apps.data_factory.exceptions import DATA_SOURCE_DEFAULT_DATABASE_REQUIRED
            raise DataFactoryError(DATA_SOURCE_DEFAULT_DATABASE_REQUIRED) from error
        if isinstance(error, sqlalchemy_error.IntegrityError):
            message = DATA_SOURCE_SQL_DATABASE_INVALID_CODE_SQL_DATABASE_INVALID
        elif isinstance(error, sqlalchemy_error.DataError):
            message = DATA_SOURCE_SQL_PARAMETER_INVALID
        elif isinstance(error, sqlalchemy_error.ProgrammingError):
            message = DATA_SOURCE_SQL_DATABASE_INVALID
        elif isinstance(error, sqlalchemy_error.OperationalError):
            if any(marker in normalized for marker in (
                    'syntax error', 'sql syntax', 'no such table', 'unknown column',
                    'undefined table', 'undefined column', 'does not exist',
            )):
                message = DATA_SOURCE_SQL_DATABASE_INVALID
            elif any(marker in normalized for marker in ('timeout', 'timed out', 'lock wait timeout')):
                message = DATA_SOURCE_SQL_EXECUTION_TIMEOUT
            else:
                message = DATA_SOURCE_SQL_EXECUTION_FAILED
        elif isinstance(error, sqlalchemy_error.InterfaceError):
            message = DATA_SOURCE_SQL_EXECUTION_FAILED
        elif isinstance(error, sqlalchemy_error.StatementError):
            message = DATA_SOURCE_SQL_PARAMETER_INVALID
        elif isinstance(error, sqlalchemy_error.TimeoutError):
            message = DATA_SOURCE_SQL_EXECUTION_TIMEOUT
        else:
            # OperationalError/InterfaceError/DBAPIError 既可能是连接错误，也可能是库表不存在等执行错误。
            message = DATA_SOURCE_SQL_EXECUTION_FAILED
        raise DataFactoryError(message, value=(type_name, detail)) from error

    @classmethod
    def raise_redis_error(cls, database, error: Exception) -> None:
        detail = cls.safe_detail(database, error)
        normalized = detail.upper()
        if isinstance(error, (socket.timeout, socket.gaierror, ssl.SSLError, TimeoutError, OSError)):
            message = DATA_SOURCE_REDIS_NETWORK_FAILED
        elif normalized.startswith(('NOAUTH', 'WRONGPASS', 'NOPERM')):
            message = DATA_SOURCE_PERMISSION_FAILED
        elif 'WRONGTYPE' in normalized:
            message = DATA_SOURCE_TYPE_INVALID
        elif normalized.startswith(('READONLY', 'MISCONF')):
            message = DATA_SOURCE_WRITE_NOT_ALLOWED
        elif (
                normalized.startswith('ERR')
                and any(marker in normalized for marker in ('SYNTAX', 'UNKNOWN COMMAND', 'WRONG NUMBER'))
        ):
            message = DATA_SOURCE_PARAMETER_INVALID
        else:
            message = DATA_SOURCE_FAILED
        raise DataFactoryError(message, value=(detail,)) from error

    @classmethod
    def raise_elasticsearch_http_error(cls, database, error: urllib_error.HTTPError) -> None:
        status = error.code
        detail = cls.safe_detail(database, error)
        error_type = ''
        try:
            payload = json.loads(error.read().decode('utf-8'))
            error_payload = payload.get('error', {}) if isinstance(payload, dict) else {}
            if isinstance(error_payload, dict):
                root_cause = error_payload.get('root_cause') or []
                cause = root_cause[0] if root_cause and isinstance(root_cause[0], dict) else error_payload
                error_type = str(cause.get('type') or error_payload.get('type') or '')
                reason = cause.get('reason') or error_payload.get('reason')
                if reason:
                    detail = f'{error_type}: {reason}' if error_type else str(reason)
            elif error_payload:
                detail = str(error_payload)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, AttributeError, ValueError):
            pass
        detail = cls.safe_detail(database, Exception(detail))
        if status == 400 or error_type in {
            'parsing_exception', 'x_content_parse_exception', 'query_shard_exception',
        }:
            message = DATA_SOURCE_ELASTICSEARCH_QUERY_INVALID
            values = (detail,)
        elif status == 401:
            message = DATA_SOURCE_ELASTICSEARCH_AUTHENTICATION_FAILED
            values = (detail,)
        elif status == 403:
            message = DATA_SOURCE_PERMISSION_FAILED_CODE_PERMISSION_FAILED
            values = (detail,)
        elif status == 404 or error_type == 'index_not_found_exception':
            message = DATA_SOURCE_NOT_FOUND
            values = (detail,)
        elif status == 429:
            message = DATA_SOURCE_REQUEST_SERVICE_INVALID
            values = (detail,)
        else:
            message = DATA_SOURCE_REQUEST_FAILED
            values = (status, detail)
        raise DataFactoryError(message, value=values) from error

    @classmethod
    def raise_elasticsearch_transport_error(cls, database, error: Exception) -> None:
        detail = cls.safe_detail(database, error)
        if isinstance(error, json.JSONDecodeError):
            message = DATA_SOURCE_JSON_PARSE_INVALID
        elif isinstance(error, (urllib_error.URLError, socket.timeout, ssl.SSLError, TimeoutError, OSError)):
            message = DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED
        else:
            message = DATA_SOURCE_FAILED_CODE_FAILED
        raise DataFactoryError(message, value=(detail,)) from error
