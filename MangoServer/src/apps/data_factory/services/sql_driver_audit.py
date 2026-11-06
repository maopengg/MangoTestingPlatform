"""补齐 Inspector/结构巡检等 SQLAlchemy 调用；已持有业务审计时不重复记录。"""

from time import perf_counter

from sqlalchemy import event

from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum


class AuditedResultCursor:
    def __init__(self, cursor, handle):
        self.cursor = cursor
        self.handle = handle
        self.rows = []
        self.count = 0
        self.preview_size = 0
        self.truncated = False
        self.duration_ms = float(handle.record.duration_ms or 0)

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
        columns = [item[0] for item in self.cursor.description or []]
        record = self.handle.record
        preview, truncated = SqlExecutionAuditService.result_preview({'columns': columns, 'rows': self.rows})
        record.result_preview = preview
        record.result_truncated = truncated or self.truncated
        record.row_count = self.count
        record.duration_ms = round(self.duration_ms, 2)
        record.is_slow = record.duration_ms > record.slow_threshold_ms
        SqlExecutionAuditService.save_completion(record, update_fields=[
            'result_preview', 'result_truncated', 'row_count', 'duration_ms', 'is_slow', 'update_time',
        ])

    def fetchone(self):
        started = perf_counter()
        row = self.cursor.fetchone()
        self.capture([] if row is None else [row], (perf_counter() - started) * 1000)
        return row

    def fetchmany(self, *args, **kwargs):
        started = perf_counter()
        rows = self.cursor.fetchmany(*args, **kwargs)
        self.capture(rows, (perf_counter() - started) * 1000)
        return rows

    def fetchall(self):
        started = perf_counter()
        rows = self.cursor.fetchall()
        self.capture(rows, (perf_counter() - started) * 1000)
        return rows

    def close(self):
        try:
            return self.cursor.close()
        finally:
            SqlExecutionAuditService.notify_slow(self.handle.record)


class SqlDriverAuditService:
    @staticmethod
    def attach(engine, database):
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService

        @event.listens_for(engine, 'commit')
        def check_commit_ownership(connection):
            from src.apps.data_factory.services.cleanup_persistence import CleanupPersistenceService
            CleanupPersistenceService.check()

        def start(statement, parameters=None, stage=DatasourceAuditStageEnum.STATEMENT.value, parent=None):
            source = {'source_type': DatasourceAuditSourceEnum.METADATA.value,
                      'source_id': database.id, **SqlExecutionAuditService.current_source(), 'source_stage': stage}
            if parent is not None:
                source.update(parent.record.source_detail)
                source.pop('request_signature', None)
                source['parent_sql_execution_id'] = parent.record.id
                source['source_stage'] = (DatasourceAuditStageEnum.GENERATED_KEY_LOOKUP.value
                                          if parent.record.source_stage == 'create' else DatasourceAuditStageEnum.NESTED_QUERY.value)
            return SqlExecutionAuditService.start(
                database=database, sql=statement, parameters={'bindings': parameters} if parameters else {},
                source_context=source, request_id=None, started_monotonic=perf_counter(),
            )

        @event.listens_for(engine, 'before_cursor_execute')
        def before_execute(connection, cursor, statement, parameters, context, executemany):
            from src.apps.data_factory.services.cleanup_persistence import CleanupPersistenceService
            CleanupPersistenceService.check()
            context.mango_audit = None
            context.mango_permit = DatasourceGovernorService.operation(database, physical=True)
            admission = context.mango_permit.__enter__()
            context.mango_admission_wait_ms = (admission or {}).get('admission_wait_ms', 0)
            try:
                prepare_audit(statement, parameters, context)
            except BaseException as error:
                context.mango_permit.__exit__(type(error), error, error.__traceback__)
                context.mango_permit = None
                raise

        def prepare_audit(statement, parameters, context):
            if statement.lstrip().upper().startswith(('SET TRANSACTION ', 'PRAGMA QUERY_ONLY', 'SAVEPOINT ', 'RELEASE SAVEPOINT ')):
                return
            parent = SqlExecutionAuditService.active()
            if parent is not None and not parent.statement_claimed:
                parent.statement_claimed = True
                return
            context.mango_audit = start(statement, parameters, parent=parent)
            # 此审计在取得名额后才创建；单独补记前置等待，不混入 SQL 执行时长。
            context.mango_audit.admission_wait_ms = context.mango_admission_wait_ms
            if parent is not None:
                parent.children.append(context.mango_audit)

        @event.listens_for(engine, 'after_cursor_execute')
        def after_execute(connection, cursor, statement, parameters, context, executemany):
            permit = getattr(context, 'mango_permit', None)
            if permit is not None:
                permit.__exit__(None, None, None)
                context.mango_permit = None
            handle = getattr(context, 'mango_audit', None)
            if handle is None:
                return
            SqlExecutionAuditService.finish_success(handle, {
                'affected_rows': max(cursor.rowcount, 0) if not cursor.description else 0,
                'columns': [item[0] for item in cursor.description or []],
            }, round((perf_counter() - handle.started_monotonic) * 1000, 2))
            if cursor.description:
                context.cursor = AuditedResultCursor(cursor, handle)

        @event.listens_for(engine, 'handle_error')
        def failed(error_context):
            if error_context.connection is not None and (error_context.is_disconnect
                    or DatasourceGovernorService.outcome_unknown(error_context.original_exception)):
                error_context.original_exception._datasource_outcome_unknown = True
            permit = getattr(error_context.execution_context, 'mango_permit', None)
            if permit is not None:
                error = error_context.original_exception
                permit.__exit__(type(error), error, error.__traceback__)
                error_context.execution_context.mango_permit = None
            handle = getattr(error_context.execution_context, 'mango_audit', None)
            if handle is not None:
                SqlExecutionAuditService.finish_failure(handle, error_context.original_exception,
                                                       round((perf_counter() - handle.started_monotonic) * 1000, 2))

        # 连接初始化 SQL 属于驱动协议；连接尝试单独记探测，不记录凭据交换。
        @event.listens_for(engine, 'do_connect')
        def connect(dialect, connection_record, args, kwargs):
            return connect_admitted(dialect, connection_record, args, kwargs)

        def connect_admitted(dialect, connection_record, args, kwargs):
            from src.apps.data_factory.services.datasource_connection import GovernedDbapiConnection
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
