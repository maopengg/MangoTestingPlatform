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
    DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT,
    DATA_SOURCE_REQUEST_FAILED,
    DataFactoryError,
    DATA_SOURCE_SERVER_QUERY_LIMIT_EXCEEDED,
)
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class DataSourceErrorService:
    """把不同驱动和协议的错误统一转成可直接展示的业务错误。"""

    @staticmethod
    def audit_reason(error):
        """审计只保存可信错误类别，不保存驱动可能附带的SQL参数、响应体或凭据。"""
        reasons = {1062: '唯一键冲突，请检查本轮生成值是否与已有数据重复',
                   1064: 'SQL语法错误，请检查用例中的SQL',
                   1054: 'SQL引用的字段不存在，请核对表结构和用例SQL',
                   1146: 'SQL引用的数据表不存在，请核对库名和表名',
                   1044: '数据库账号无访问权限，请核对数据源授权',
                   1045: '数据库认证失败，请核对数据源账号和密码',
                   1205: '数据库锁等待超时，请检查并发事务与锁持有情况',
                   1213: '数据库检测到死锁，请检查并发事务的访问顺序',
                   1406: '写入内容超过字段长度，请检查生成规则或用例参数',
                   1451: '记录仍被外键引用，无法删除，请检查关联数据清理顺序',
                   1452: '写入引用的父记录不存在，请检查前置数据和关联字段',
                   1525: '日期或字段值不合法，请检查用例SQL中的比较值、格式及字段类型',
                   2003: '无法连接数据库，请检查数据源地址、端口和网络',
                   2006: '数据库连接已断开，请核查原操作结果，勿直接重放写入',
                   2013: '数据库操作过程中连接中断，请核查原操作结果，勿直接重放写入',
                   3024: '查询超过数据库执行时间限制，请检查查询范围和索引',
                   3141: 'JSON函数参数不是合法JSON，请检查用例SQL中的JSON输入、空字符串及字段内容，修正后重试'}
        seen = set()
        while isinstance(error, BaseException) and id(error) not in seen:
            seen.add(id(error))
            number = DataSourceErrorService.server_error_number(error)
            if number in reasons:
                return f'数据库错误 {number}：{reasons[number]}'
            state = getattr(error, 'sqlstate', None) or getattr(error, 'pgcode', None)
            postgres = {'23505': '唯一键冲突', '23503': '外键约束冲突', '42601': 'SQL语法错误',
                        '42P01': '数据表不存在', '42703': '字段不存在', '42501': '权限不足'}
            if state in postgres:
                return f'数据库错误 {state}：{postgres[state]}，请检查用例SQL、表结构和权限'
            if isinstance(error, urllib_error.HTTPError):
                return f'数据源返回HTTP {error.code}，请检查请求内容、目标资源及访问权限'
            from redis.exceptions import ResponseError
            if isinstance(error, ResponseError):
                prefix = str(error).split(' ', 1)[0].upper()
                redis_reasons = {'WRONGTYPE': 'Redis键类型与命令不匹配，请检查目标键及命令',
                                 'NOPERM': 'Redis账号无权执行命令，请核对数据源授权',
                                 'NOAUTH': 'Redis未完成认证，请核对数据源认证配置',
                                 'WRONGPASS': 'Redis认证失败，请核对用户名和密码',
                                 'READONLY': 'Redis连接指向只读节点，不能执行写操作，请核对数据源地址'}
                if prefix in redis_reasons:
                    return redis_reasons[prefix]
                return 'Redis服务端拒绝命令，请检查命令参数、键类型及访问权限'
            if isinstance(error, DataFactoryError) and 34173 <= error.code <= 34194:
                return error.msg
            error = getattr(error, 'orig', None) or error.__cause__
        return None

    @staticmethod
    def confirmed_rejection(error):
        """只认驱动返回的服务器错误码；未知异常、断连及提交结果丢失不能推定拒绝。"""
        seen = set()
        rejected = False
        while isinstance(error, BaseException) and id(error) not in seen:
            seen.add(id(error))
            if (getattr(error, '_datasource_outcome_unknown', False)
                    or getattr(error, 'connection_invalidated', False)):
                return False
            if isinstance(error, urllib_error.HTTPError):
                return 400 <= error.code < 500 and error.code != 408
            from redis.exceptions import ResponseError
            if isinstance(error, ResponseError):
                # 服务端已返回错误响应，操作已结束；不代表无副作用，也不允许重放写入。
                return True
            if isinstance(error, (OSError, TimeoutError)) or 'Timeout' in type(error).__name__:
                return False
            from src.apps.data_factory.exceptions import DATASOURCE_AUDIT_COMPLETION_FAILED, DATASOURCE_SETTLEMENT_FAILED
            if getattr(error, 'code', None) in (DATASOURCE_AUDIT_COMPLETION_FAILED.code, DATASOURCE_SETTLEMENT_FAILED.code):
                return False
            number = error.args[0] if error.args else None
            sqlstate = getattr(error, 'sqlstate', None) or getattr(error, 'pgcode', None)
            if type(number) is int:
                if number in (2006, 2013, 2055):
                    return False
                # 只列确定拒绝语句的错误；服务端通信错误也可能使用1000段，不能整段放行。
                rejected |= number in {
                    1044, 1045, 1049, 1050, 1051, 1052, 1054, 1060, 1061, 1062, 1064,
                    1091, 1109, 1110, 1136, 1142, 1143, 1146, 1149, 1193, 1205, 1213, 1227,
                    1222, 1241, 1242, 1264, 1265, 1292, 1304, 1305, 1364, 1366,
                    1406, 1451, 1452, 1525, 1582, 1690, 3024, 3065, 3140, 3141, 3143,
                }
            if isinstance(sqlstate, str) and len(sqlstate) == 5:
                if sqlstate.startswith('08') or sqlstate in ('40003', '08007'):
                    return False
                rejected |= sqlstate[:2] in ('22', '23', '28', '3D', '3F', '40', '42', '53', '54') or sqlstate == '57014'
            reason = getattr(error, 'reason', None)
            error = getattr(error, 'orig', None) or error.__cause__ or (
                reason if isinstance(reason, BaseException) else None)
        return rejected

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

        if database.db_type == DataSourceTypeEnum.MYSQL.value and cls.server_error_number(error) == 3024:
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            raise DatasourceInfrastructureService.annotate(
                DataFactoryError(DATA_SOURCE_SERVER_QUERY_LIMIT_EXCEEDED)) from error

        type_name = DataSourceTypeEnum.obj().get(database.db_type, database.db_type)
        detail = cls.safe_detail(database, error)
        normalized = detail.lower()
        if database.db_type == DataSourceTypeEnum.MYSQL.value and not database.database_name and 'no database selected' in normalized:
            from src.apps.data_factory.exceptions import DATA_SOURCE_DEFAULT_DATABASE_REQUIRED
            raise DataFactoryError(DATA_SOURCE_DEFAULT_DATABASE_REQUIRED) from error
        if (database.db_type == DataSourceTypeEnum.MYSQL.value
                and cls.server_error_number(error) == 3141 and cls.confirmed_rejection(error)):
            message = DATA_SOURCE_SQL_PARAMETER_INVALID
            detail = cls.audit_reason(error)
        elif isinstance(error, sqlalchemy_error.IntegrityError):
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
        translated = DataFactoryError(message, value=(type_name, detail))
        if (getattr(error, '_datasource_operation_not_sent', False)
                and not getattr(error, '_datasource_outcome_unknown', False)
                and not getattr(error, 'connection_invalidated', False)):
            translated._datasource_operation_not_sent = True
        raise translated from error

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
        failure = DataFactoryError(message, value=values)
        failure._elasticsearch_http_status = status
        failure._elasticsearch_error_type = error_type
        raise failure from error

    @classmethod
    def is_elasticsearch_version_conflict(cls, error):
        chain = list(cls.execution_error_chain(error))
        if any(getattr(value, '_datasource_audit_failure_code', None)
               or getattr(value, '_datasource_outcome_unknown', False)
               or getattr(value, '_datasource_unknown_permit', None) for value in chain):
            return False
        return any(getattr(value, '_elasticsearch_http_status', None) == 409
                   and getattr(value, '_elasticsearch_error_type', None) == 'version_conflict_engine_exception'
                   for value in chain)

    @classmethod
    def raise_elasticsearch_transport_error(cls, database, error: Exception, *, timeout=None) -> None:
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService

        if SqlExecutionAuditService.is_timeout(error):
            from src.apps.test_center.services.datasource.data_source import DataSourceConnectionService
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            failure = DataFactoryError(DATA_SOURCE_ELASTICSEARCH_REQUEST_TIMEOUT)
            seconds = DataSourceConnectionService.timeout_seconds() if timeout is None else timeout
            failure.msg += f'。当前请求超时配置为 {seconds} 秒'
            cls.preserve_execution_state(error, failure)
            raise DatasourceInfrastructureService.annotate(failure, database_id=getattr(database, 'id', None)) from error
        detail = cls.safe_detail(database, error)
        if isinstance(error, json.JSONDecodeError):
            message = DATA_SOURCE_JSON_PARSE_INVALID
        elif isinstance(error, (urllib_error.URLError, socket.timeout, ssl.SSLError, TimeoutError, OSError)):
            message = DATA_SOURCE_ELASTICSEARCH_NETWORK_FAILED
        else:
            message = DATA_SOURCE_FAILED_CODE_FAILED
        raise cls.preserve_execution_state(error, DataFactoryError(message, value=(detail,))) from error

    @staticmethod
    def execution_error_chain(error):
        """只沿显式驱动异常链查找执行标识，不读取异常正文或任意上下文。"""
        seen = set()
        pending = [error]
        while pending and len(seen) < 32:
            current = pending.pop(0)
            if not isinstance(current, BaseException) or id(current) in seen:
                continue
            seen.add(id(current))
            yield current
            pending.extend((current.__cause__, getattr(current, 'orig', None), getattr(current, 'reason', None)))

    @classmethod
    def unknown_operation_permit(cls, error):
        import re
        for current in cls.execution_error_chain(error):
            permit = getattr(current, '_datasource_unknown_permit', None)
            if (isinstance(permit, (tuple, list)) and len(permit) == 2
                    and all(isinstance(value, str) and re.fullmatch(r'[a-f0-9]{32}', value) for value in permit)):
                return tuple(permit)
        return None
    @classmethod
    def preserve_execution_state(cls, error, failure):
        """协议异常包装不能丢失精确名额；不复制 __dict__、SQL 或连接信息。"""
        permit = cls.unknown_operation_permit(error)
        if permit is not None:
            failure._datasource_unknown_permit = permit
        for current in cls.execution_error_chain(error):
            for attribute in ('_datasource_outcome_unknown', '_datasource_settlement_failed'):
                if getattr(current, attribute, False) is True:
                    setattr(failure, attribute, True)
            request_id = getattr(current, '_datasource_audit_request_id', None)
            if (isinstance(request_id, str) and request_id
                    and not getattr(failure, '_datasource_audit_request_id', None)):
                failure._datasource_audit_request_id = request_id
        return failure

    @staticmethod
    def server_error_number(error):
        seen = set()
        while isinstance(error, BaseException) and id(error) not in seen:
            seen.add(id(error))
            number = error.args[0] if error.args else None
            if type(number) is int:
                return number
            error = getattr(error, 'orig', None) or error.__cause__
        return None
