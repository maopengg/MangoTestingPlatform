from src.apps.data_factory.exceptions import (
    DataFactoryError, DATASOURCE_OPERATION_COST_EXCEEDED, DATA_SOURCE_QUERY_RESULT_LIMIT_EXCEEDED,
)


class DatasourceCostService:
    MAX_SQL_CHARACTERS = 100_000
    @classmethod
    def sql(cls, sql):
        if not isinstance(sql, str):
            cls.reject('SQL 内容必须为字符串。请修改用例的数据库操作配置', not_sent=True)
        if len(sql) > cls.MAX_SQL_CHARACTERS:
            cls.reject(f'SQL 文本过长：最多允许 {cls.MAX_SQL_CHARACTERS} 个字符，当前为 {len(sql)} 个。请检查是否拼接了大量条件或重复SQL，并拆分操作', not_sent=True)
        import sqlparse
        import re
        from sqlparse import tokens
        statements = sqlparse.parse(sql)
        normalized = ' '.join(sqlparse.format(sql, strip_comments=True).strip().upper().split())
        if len(statements) != 1 or normalized.startswith((
                'SET ', 'USE ', 'BEGIN', 'COMMIT', 'ROLLBACK', 'LOCK ', 'UNLOCK ', 'CALL ',
                'PREPARE ', 'EXECUTE ', 'CREATE TEMPORARY ', 'START TRANSACTION')):
            operation = '多条SQL' if len(statements) != 1 else normalized.split(' ', 1)[0]
            cls.reject(f'当前SQL包含不支持的操作：{operation}。平台共享连接不支持多语句、会话变更、显式事务或临时状态，请修改用例SQL，每次提交一条独立SQL', not_sent=True)
        executable = ''.join(token.value if token.ttype not in tokens.Literal.String
                             and token.ttype not in tokens.Comment else ' '
                             for statement in statements for token in statement.flatten()).upper()
        if (re.search(r'(?<![A-Z0-9_])@@?[A-Z_]', executable) or ':=' in executable or re.search(
                r'\b(?:GET_LOCK|RELEASE_LOCK|RELEASE_ALL_LOCKS|SLEEP|BENCHMARK|LOAD_FILE|LAST_INSERT_ID|FOUND_ROWS|ROW_COUNT)\s*\('
                r'|\bINTO\s+(?:OUTFILE|DUMPFILE)\b', executable)):
            function = re.search(r'\b(GET_LOCK|RELEASE_LOCK|RELEASE_ALL_LOCKS|SLEEP|BENCHMARK|LOAD_FILE|LAST_INSERT_ID|FOUND_ROWS|ROW_COUNT)\s*\(|\bINTO\s+(OUTFILE|DUMPFILE)\b', executable)
            operation = next((value for value in function.groups() if value), '') if function else '用户会话变量或赋值'
            cls.reject(f'当前SQL使用了不支持的 {operation}。该操作依赖或影响共享会话，或产生额外副作用，请修改用例SQL', not_sent=True)

    @staticmethod
    def reject(reason, *, not_sent=False):
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        error = DataFactoryError(DATASOURCE_OPERATION_COST_EXCEEDED, value=(reason,))
        error._datasource_not_sent = not_sent
        DatasourceInfrastructureService.annotate(error)
        DatasourceInfrastructureService.capture(error)
        raise error

    @staticmethod
    def abort_result(connection, result, *, limit, observed_rows, is_write=False):
        error = DataFactoryError(DATA_SOURCE_QUERY_RESULT_LIMIT_EXCEEDED,
                                 value=(limit, observed_rows),
                                 details={'limit': limit, 'observed_rows': observed_rows, 'is_write': is_write})
        error._datasource_outcome_unknown = is_write
        try:
            connection.invalidate()
        except Exception:
            # 关闭未确认时仍保留未知状态，不能因超限是配置问题就放开安全围栏。
            error._datasource_outcome_unknown = True
        finally:
            try:
                result.close()
            except Exception:
                from src.common.logging import log
                log.system.warning('超量结果游标关闭异常，未返回部分结果')
            raise error

    @classmethod
    def redis(cls, parts):
        command = parts[0].upper()
        if command in {'AUTH', 'SELECT', 'MULTI', 'EXEC', 'WATCH', 'UNWATCH', 'DISCARD', 'SUBSCRIBE',
                       'PSUBSCRIBE', 'MONITOR', 'BLPOP', 'BRPOP', 'BZPOPMIN', 'BZPOPMAX', 'CLIENT',
                       'KEYS'}:
            reason = ('全库扫描会阻塞共享数据源，请使用受控SCAN遍历' if command == 'KEYS' else
                      '会改变连接会话' if command in {'AUTH', 'SELECT', 'MULTI', 'EXEC', 'WATCH', 'UNWATCH', 'DISCARD', 'CLIENT'} else
                      '会阻塞连接或进入持续订阅状态')
            cls.reject(f'当前Redis命令 {command} 不支持通过共享连接执行：{reason}。请修改用例操作', not_sent=True)
        from src.apps.data_factory.services.data_source_query import DataFactoryDatasourceQuery
        writes = {'SET', 'SETEX', 'PSETEX', 'SETNX', 'MSET', 'DEL', 'UNLINK', 'EXPIRE', 'PEXPIRE',
                  'EXPIREAT', 'PEXPIREAT', 'PERSIST', 'INCR', 'INCRBY', 'INCRBYFLOAT', 'DECR', 'DECRBY',
                  'HSET', 'HSETNX', 'HDEL', 'HINCRBY', 'HINCRBYFLOAT', 'SADD', 'SREM',
                  'LPUSH', 'RPUSH', 'LPOP', 'RPOP', 'LSET', 'ZADD', 'ZREM', 'ZINCRBY'}
        if command not in DataFactoryDatasourceQuery.REDIS_READ_COMMANDS | writes:
            safe_command = command if command.isascii() and command.isalpha() and len(command) <= 32 else '未识别命令'
            cls.reject(f'平台暂不支持Redis命令 {safe_command}，本次未执行。请联系平台管理员确认是否需要支持该命令', not_sent=True)
        # SCAN 的 COUNT 是提示值，LRANGE -1 是合法语义；不通过改写范围改变断言。
        # 实际响应仍由 RESP 解析器按配置的元素数和字节数完整校验，超限绝不返回部分结果。

    @classmethod
    def elasticsearch(cls, index, query):
        if not isinstance(index, str) or not index:
            cls.reject('ES查询未填写有效索引名称。请检查用例的数据源查询配置', not_sent=True)
        for name, default in (('from', 0), ('size', 20)):
            value = query.get(name, default)
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                cls.reject(f'ES分页参数 {name} 必须为整数，当前值类型为 {type(value).__name__}。请修改用例查询配置', not_sent=True)
            if parsed < 0:
                cls.reject(f'ES分页参数 {name} 不能小于0，当前为 {parsed}。请修改用例查询配置', not_sent=True)
        # 不按字段名/DSL形状猜测实际成本；并发、速率、I/O超时和完整响应限制仍生效。
