"""补齐 Inspector/结构巡检等 SQLAlchemy 调用；已持有业务审计时不重复记录。"""

from time import perf_counter

from sqlalchemy import event

from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
from src.apps.data_factory.enums.performance import DatasourceTimingPhaseEnum as Phase
from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing


class TimedResultCursor:
    def __init__(self, cursor):
        self.cursor = cursor

    def __getattr__(self, key):
        return getattr(self.cursor, key)

    def fetchone(self):
        with Timing.measure(Phase.FETCH):
            return self.cursor.fetchone()

    def fetchmany(self, *args, **kwargs):
        with Timing.measure(Phase.FETCH):
            return self.cursor.fetchmany(*args, **kwargs)

    def fetchall(self):
        with Timing.measure(Phase.FETCH):
            return self.cursor.fetchall()


class AuditedResultCursor:
    def __init__(self, cursor, handle):
        self.cursor = cursor
        self.handle = handle
        self.rows = []
        self.count = 0
        self.preview_size = 0
        self.truncated = False
        self.duration_ms = (perf_counter() - handle.started_monotonic) * 1000
        self.finished = False
        self.fully_read = False

    def __getattr__(self, key):
        return getattr(self.cursor, key)

    def capture(self, rows, elapsed):
        self.duration_ms += elapsed
        for row in rows:
            self.count += 1
            if self.preview_size < 1000:
                value = list(row)
                self.rows.append(value)
                self.preview_size += sum(len(str(item)) for item in value)
            else:
                self.truncated = True

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        self.handle.record.source_detail = {**self.handle.record.source_detail,
                                           'result_fully_read': self.fully_read}
        if error is not None:
            self.handle.record.row_count = self.count
            preview, truncated = SqlExecutionAuditService.result_preview({
                'columns': [item[0] for item in self.cursor.description or []], 'rows': self.rows})
            self.handle.record.result_preview = preview
            self.handle.record.result_truncated = truncated or self.truncated
            SqlExecutionAuditService.finish_failure(self.handle, error, self.duration_ms)
        else:
            SqlExecutionAuditService.finish_success(self.handle, {
                'columns': [item[0] for item in self.cursor.description or []],
                'rows': self.rows, 'row_count': self.count, 'affected_rows': 0,
                'truncated': self.truncated,
            }, self.duration_ms)

    def fetch(self, method, *args, all_rows=False, **kwargs):
        started = perf_counter()
        try:
            value = getattr(self.cursor, method)(*args, **kwargs)
        except BaseException as error:
            self.duration_ms += (perf_counter() - started) * 1000
            self.finish(error)
            raise
        rows = ([] if value is None else [value]) if method == 'fetchone' else value
        self.capture(rows, (perf_counter() - started) * 1000)
        if all_rows or not rows:
            self.fully_read = True
            self.finish()
        return value

    def fetchone(self):
        return self.fetch('fetchone')

    def fetchmany(self, *args, **kwargs):
        return self.fetch('fetchmany', *args, **kwargs)

    def fetchall(self):
        return self.fetch('fetchall', all_rows=True)

    def close(self):
        try:
            self.finish()
            return self.cursor.close()
        except BaseException as error:
            self.finish(error)
            raise


class SqlDriverAuditService:
    @staticmethod
    def attach(engine, database):
        from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService
        engine.pool._mango_database_id = database.id

        @event.listens_for(engine, 'commit')
        def check_commit_ownership(connection):
            from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
            CleanupPersistenceService.check()

        def transaction_operation(method, operation):
            def execute(connection):
                parent = SqlExecutionAuditService.active()
                context = dict(parent.record.source_detail) if parent is not None else {}
                if parent is not None:
                    context['parent_request_id'] = parent.record.request_id
                with SqlExecutionAuditService.source(context):
                    return SqlExecutionAuditService.call(database, operation, lambda: method(connection),
                        stage=DatasourceAuditStageEnum.TRANSACTION.value,
                        source_type=DatasourceAuditSourceEnum.METADATA.value, independent=True)
            return execute

        engine.dialect.do_commit = transaction_operation(engine.dialect.do_commit, 'COMMIT')
        engine.dialect.do_rollback = transaction_operation(engine.dialect.do_rollback, 'ROLLBACK')

        def start(statement, parameters=None, stage=DatasourceAuditStageEnum.STATEMENT.value, parent=None):
            source = {'source_type': DatasourceAuditSourceEnum.METADATA.value,
                      'source_id': database.id, **SqlExecutionAuditService.current_source(), 'source_stage': stage}
            if parent is not None:
                source.update(parent.record.source_detail)
                source.pop('request_signature', None)
                source['parent_request_id'] = parent.record.request_id
                if parent.record.id is not None:
                    source['parent_sql_execution_id'] = parent.record.id
                source['source_stage'] = (stage if stage != DatasourceAuditStageEnum.STATEMENT.value else
                    (DatasourceAuditStageEnum.GENERATED_KEY_LOOKUP.value if parent.record.source_stage == 'create'
                     else DatasourceAuditStageEnum.NESTED_QUERY.value))
            return SqlExecutionAuditService.start(
                database=database, sql=statement, parameters={'bindings': parameters} if parameters else {},
                source_context=source, request_id=None, started_monotonic=perf_counter(),
            )

        @event.listens_for(engine, 'before_cursor_execute')
        def before_execute(connection, cursor, statement, parameters, context, executemany):
            from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
            CleanupPersistenceService.check()
            context.mango_audit = None
            context.mango_timing_started = Timing.snapshot()
            try:
                prepare_audit(statement, parameters, context)
                context.mango_execute_started = perf_counter()
            except BaseException as error:
                error._datasource_operation_not_sent = True
                handle = getattr(context, 'mango_audit', None)
                if handle is not None:
                    context.mango_audit = None
                    SqlExecutionAuditService.finish_failure(handle, error,
                        round((perf_counter() - handle.started_monotonic) * 1000, 2))
                raise

        def prepare_audit(statement, parameters, context):
            control = statement.lstrip().upper().startswith((
                'SET TRANSACTION ', 'PRAGMA QUERY_ONLY', 'SAVEPOINT ', 'RELEASE SAVEPOINT ', 'ROLLBACK TO SAVEPOINT '))
            parent = SqlExecutionAuditService.active()
            if parent is not None and not parent.statement_claimed and not control:
                parent.statement_claimed = True
                return
            context.mango_audit = start(statement, parameters, parent=parent,
                stage=DatasourceAuditStageEnum.TRANSACTION.value if control else DatasourceAuditStageEnum.STATEMENT.value)
            # 各段耗时单独累计；不将连接等待重复算作物理 SQL 执行。
            context.mango_audit.timing_started = context.mango_timing_started
            if parent is not None:
                parent.children.append(context.mango_audit)

        def execute_physical(dialect, callback, cursor, statement, parameters, context):
            started = perf_counter()
            try:
                try:
                    callback()
                finally:
                    Timing.add(Phase.EXECUTE, perf_counter() - started)
                    context.mango_execute_started = None
            except BaseException as error:
                try:
                    disconnected = isinstance(error, dialect.loaded_dbapi.Error) and dialect.is_disconnect(
                        error, context.root_connection.connection, cursor)
                except Exception:
                    # 无法判明连接状态时，不能把未知传输错误当成确定失败。
                    disconnected = True
                if disconnected:
                    error._datasource_outcome_unknown = True
                if disconnected or DatasourceGovernorService.outcome_unknown(error):
                    # 未知连接不得回池再次承载业务；只退役本次物理连接，原操作名额仍待核查。
                    try:
                        context.root_connection.invalidate(error)
                    except Exception:
                        from src.common.logging import log
                        log.system.warning('event=datasource_unknown_connection_retirement_pending '
                                           'database_id=%s action=verify_physical_close', database.id)
                handle = getattr(context, 'mango_audit', None)
                if handle is not None:
                    context.mango_audit = None
                    SqlExecutionAuditService.finish_failure(handle, error,
                        round((perf_counter() - handle.started_monotonic) * 1000, 2))
                raise
            else:
                return True

        @event.listens_for(engine, 'do_execute')
        def execute(cursor, statement, parameters, context):
            return execute_physical(engine.dialect,
                lambda: engine.dialect.do_execute(cursor, statement, parameters, context),
                cursor, statement, parameters, context)

        @event.listens_for(engine, 'do_executemany')
        def execute_many(cursor, statement, parameters, context):
            return execute_physical(engine.dialect,
                lambda: engine.dialect.do_executemany(cursor, statement, parameters, context),
                cursor, statement, parameters, context)

        @event.listens_for(engine, 'do_execute_no_params')
        def execute_no_params(cursor, statement, context):
            return execute_physical(engine.dialect,
                lambda: engine.dialect.do_execute_no_params(cursor, statement, context),
                cursor, statement, None, context)

        @event.listens_for(engine, 'after_cursor_execute')
        def after_execute(connection, cursor, statement, parameters, context, executemany):
            started = getattr(context, 'mango_execute_started', None)
            if started is not None:
                Timing.add(Phase.EXECUTE, perf_counter() - started)
                context.mango_execute_started = None
            if cursor.description:
                context.cursor = TimedResultCursor(cursor)
            handle = getattr(context, 'mango_audit', None)
            if handle is None:
                return
            if cursor.description:
                pending = connection.info.setdefault('_mango_audit_cursors', [])
                pending[:] = [value for value in pending if not value.finished]
                context.cursor = AuditedResultCursor(context.cursor, handle)
                pending.append(context.cursor)
            else:
                SqlExecutionAuditService.finish_success(handle, {
                    'affected_rows': max(cursor.rowcount, 0),
                }, round((perf_counter() - handle.started_monotonic) * 1000, 2))

        @event.listens_for(engine, 'checkin')
        def close_pending_results(connection, connection_record):
            for cursor in connection_record.info.pop('_mango_audit_cursors', []):
                if not cursor.finished:
                    cursor.close()

        @event.listens_for(engine, 'handle_error')
        def failed(error_context):
            from sqlalchemy.exc import InvalidRequestError, StatementError
            original = error_context.original_exception
            wrapped = error_context.sqlalchemy_exception
            # construct_params 在 DBAPI execute 前发现缺少绑定值；不能把该错误当成写入结果未知。
            # 不泛化到所有 StatementError：驱动拒绝、断连和事务提交异常仍走原分类。
            if (error_context.execution_context is None and not error_context.is_disconnect
                    and isinstance(wrapped, StatementError)
                    and isinstance(original, InvalidRequestError) and original.code == 'cd3x'):
                original._datasource_operation_not_sent = True
                wrapped._datasource_operation_not_sent = True
            started = getattr(error_context.execution_context, 'mango_execute_started', None)
            if started is not None:
                error_context.execution_context.mango_execute_started = None
                Timing.add(Phase.EXECUTE, perf_counter() - started)
            if error_context.connection is not None and (error_context.is_disconnect
                    or DatasourceGovernorService.outcome_unknown(error_context.original_exception)):
                error_context.original_exception._datasource_outcome_unknown = True
                if not error_context.connection.invalidated:
                    try:
                        error_context.connection.invalidate(error_context.original_exception)
                    except Exception:
                        from src.common.logging import log
                        log.system.warning('event=datasource_transaction_connection_retirement_pending database_id=%s',
                                           database.id)
            handle = getattr(error_context.execution_context, 'mango_audit', None)
            if handle is not None:
                SqlExecutionAuditService.finish_failure(handle, error_context.original_exception,
                                                       round((perf_counter() - handle.started_monotonic) * 1000, 2))

        # 连接初始化 SQL 属于驱动协议；连接尝试单独记探测，不记录凭据交换。
        @event.listens_for(engine, 'do_connect')
        def connect(dialect, connection_record, args, kwargs):
            return connect_admitted(dialect, connection_record, args, kwargs)

        def connect_admitted(dialect, connection_record, args, kwargs):
            from src.apps.data_factory.services.datasource.datasource_connection import GovernedDbapiConnection
            if SqlExecutionAuditService.active() is not None:
                return GovernedDbapiConnection.connect(database, lambda: dialect.connect(*args, **kwargs))
            handle = start('CONNECT', stage=DatasourceAuditStageEnum.CONNECT.value)
            try:
                with SqlExecutionAuditService.scope(handle):
                    connection = GovernedDbapiConnection.connect(database, lambda: dialect.connect(*args, **kwargs))
            except Exception as error:
                SqlExecutionAuditService.finish_failure(handle, error,
                                                       round((perf_counter() - handle.started_monotonic) * 1000, 2))
                raise
            SqlExecutionAuditService.finish_success(handle, {'connected': True},
                                                   round((perf_counter() - handle.started_monotonic) * 1000, 2))
            return connection
