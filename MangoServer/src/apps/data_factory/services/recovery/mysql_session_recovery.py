"""仅核查已冻结 MySQL 会话的生命周期，不接受调用方 SQL，不重放业务请求。"""
import time
import uuid
import hashlib
from contextvars import ContextVar
from pydantic import ValidationError

from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum, DatasourcePermitStateEnum
from src.apps.data_factory.schemas.performance import MysqlOperationSession, MysqlSessionRecoveryEvidence
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
from src.apps.test_center.enums.data_source import DataSourceTypeEnum

_probing = ContextVar('mysql_session_recovery_probe', default=False)


class MysqlSessionRecoveryService:
    IDENTITY_SQL = 'SELECT @@server_uuid, CONNECTION_ID(), CURRENT_USER()'
    PROBE_SQL = ('SELECT @@server_uuid, EXISTS(SELECT 1 FROM information_schema.PROCESSLIST '
                 'WHERE ID = %s), EXISTS(SELECT 1 FROM information_schema.PROCESSLIST '
                 'WHERE ID = CONNECTION_ID()), CURRENT_USER(), CONNECTION_ID()')

    @classmethod
    def capture(cls, target, raw):
        if _probing.get() or not getattr(target, 'cache_key', None):
            return None
        if hasattr(raw, '_mango_mysql_identity'):
            return raw._mango_mysql_identity
        native = getattr(raw, '_connection', raw)
        thread_id = getattr(native, 'thread_id', None)
        handshake_id = thread_id() if callable(thread_id) else None
        if type(handshake_id) is not int or handshake_id <= 0:
            return None
        try:
            # 建连元数据沿用调用方的连接超时，不额外施加更短的 Case 失败门槛。
            value = cls._query(target, raw, cls.IDENTITY_SQL, (), recovery=False)
            if not isinstance(value, (tuple, list)) or len(value) != 3 or type(value[1]) is not int or value[1] != handshake_id:
                raw._mango_mysql_identity = None
                return None
            try:
                identity = MysqlOperationSession(server_uuid=value[0].lower(), session_id=int(value[1]),
                    target_key=target.cache_key, account_digest=hashlib.sha256(value[2].encode()).hexdigest())
            except (ValidationError, TypeError, ValueError, AttributeError):
                identity = None
        except Exception as error:
            from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
            # TiDB/旧版本不支持 UUID 时不改变业务 SQL 能否执行，只关闭该连接自动核查能力。
            if not DataSourceErrorService.confirmed_rejection(error):
                raise
            identity = None
        raw._mango_mysql_identity = identity
        return identity

    @classmethod
    def _query(cls, target, raw, sql, parameters, *, recovery):
        started = time.perf_counter()
        source = {**Audit.current_source(), 'source_type': DatasourceAuditSourceEnum.METADATA.value,
                  'source_id': target.id,
                  'source_stage': (DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value if recovery
                                   else DatasourceAuditStageEnum.NETWORK_PROBE.value)}
        handle = Audit.start(database=target, sql=sql, parameters={'bindings': parameters},
                             source_context=source, request_id=None, started_monotonic=started)
        try:
            with Audit.scope(handle), Audit.source(source):
                cursor = raw.cursor()
                try:
                    cursor.execute(sql, parameters or None)
                    row = cursor.fetchone()
                finally:
                    cursor.close()
        except Exception as error:
            Audit.finish_failure(handle, error, (time.perf_counter() - started) * 1000)
            raise
        Audit.finish_success(handle, {'row_count': 1, 'session_metadata_read': True},
                             (time.perf_counter() - started) * 1000)
        if not recovery:
            raw._mango_mysql_identity_audit_id = handle.record.id
        return row

    @staticmethod
    def target(record, session):
        from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
        from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
        if record.datasource_alias_id is not None:
            binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
                record.datasource_alias_id, record.project_product_id, record.test_env)
            DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
            target = DatasourceTargetService.resolve(binding)
        else:
            from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
            database = DataFactoryQuerySelector.performance_target(record.database_id)
            if database is None:
                return None
            target = DatasourceTargetService.build(database, database_name=(record.source_detail or {}).get('database_name', ''))
        return target if target.cache_key == session.target_key and target.db_type == DataSourceTypeEnum.MYSQL.value else None

    @classmethod
    def probe(cls, record, session):
        target = cls.target(record, session)
        if target is None:
            return False
        from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource
        token = _probing.set(True)
        engine = None
        try:
            # 使用清理保留容量，但不扩大总预算；无可用容量时立即留待下一轮，不占住 Worker。
            with Governor.nonblocking_admission(), Audit.source({
                    'source_type': DatasourceAuditSourceEnum.METADATA.value, 'source_id': target.id,
                    'source_stage': DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value}):
                # 核查连接不进入共享池，核查结束立即物理关闭，不遗留闲置恢复连接。
                engine = DataFactoryDatasource._create_engine(target, timeout_seconds=3, pool_size=1)
                with engine.connect() as connection:
                    raw = connection.connection.driver_connection
                    native = getattr(raw, '_connection', raw)
                    handshake_id = native.thread_id()
                    row = cls._query(target, raw,
                        cls.PROBE_SQL, (session.session_id,), recovery=True)
                # 自身会话回读必须成功，不能把权限过滤/空响应误当成原会话已经消失。
                return bool(row and str(row[0]).lower() == session.server_uuid.lower()
                            and type(row[1]) is int and row[1] == 0
                            and type(row[2]) is int and row[2] == 1
                            and isinstance(row[3], str)
                            and hashlib.sha256(row[3].encode()).hexdigest() == session.account_digest
                            and type(row[4]) is int and type(handshake_id) is int
                            and row[4] == handshake_id and row[4] != session.session_id)
        finally:
            if engine is not None:
                engine.dispose()
            _probing.reset(token)

    @classmethod
    def recover_group(cls, group):
        from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
        nonce = uuid.uuid4().hex

        def claim(state, now):
            if state.recovery_until > now or state.recovery_next_at > now:
                return None
            candidates = [value for value in state.permits.values()
                          if value.kind in (DatasourcePermitKindEnum.OPERATION, DatasourcePermitKindEnum.CONNECTION)
                          and value.mysql_session is not None
                          and value.audit_record_id is not None
                          and (value.state == DatasourcePermitStateEnum.SUSPECT or value.expires_at <= now)]
            if not candidates:
                return None
            current = min(candidates, key=lambda value: (value.recovery_checked_at or 0,
                                                        value.unknown_since or value.expires_at))
            current.recovery_checked_at = now
            state.recovery_owner, state.recovery_until, state.recovery_next_at = nonce, now + 30, now + 5
            return current.model_dump(mode='json')

        expected = Governor.change(group, claim)
        if expected is None:
            return 0
        try:
            record = ExecutionAuditSelector.permit_evidence({expected['audit_record_id']}).get(expected['audit_record_id'])
            session = MysqlOperationSession.model_validate(expected['mysql_session'])
            if record is None or not cls.probe(record, session):
                return 0
            if expected['kind'] == DatasourcePermitKindEnum.CONNECTION.value:
                from src.apps.data_factory.schemas.performance import DatasourceConnectionClosure
                from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService
                store = Governor.store()
                def persist_closure(state, now):
                    current = state.permits.get(expected['owner'])
                    if current is None or current.model_dump(mode='json') != expected:
                        return False
                    proof = DatasourceConnectionClosure(group=group, owner=current.owner,
                        process=current.process, confirmed_at=now, basis='server_session_absent',
                        mysql_session=session)
                    store.set_if_absent(f'closed:{group}:{current.owner}', proof.model_dump(mode='json'), ttl=None)
                    return True
                if not Governor.change(group, persist_closure):
                    return 0
                return DatasourcePermitReconciliationService.recover_closed_connections(group)
            # 先持久化本次核查证据，再精确核销；响应丢失时不能丢失恢复依据。
            from src.apps.data_factory.schemas.performance import DatasourceOperationCompletion
            proof = DatasourceOperationCompletion(group=group, owner=expected['owner'],
                process=expected['process'], confirmed_at=time.time()).model_dump(mode='json')
            detail = dict(record.source_detail or {})
            proofs = list(detail.get('completed_operation_permits') or [])
            if not any(value.get('owner') == expected['owner'] for value in proofs):
                proofs.append(proof)
            detail['completed_operation_permits'] = proofs[-256:]
            detail['physical_session_recovery'] = MysqlSessionRecoveryEvidence(
                owner=expected['owner'], session_id=session.session_id,
                server_uuid=session.server_uuid, checked_at=proof['confirmed_at']).model_dump(mode='json')
            record.source_detail = detail
            Audit.save_completion(record, update_fields=['source_detail', 'update_time'])

            def settle(state, now):
                current = state.permits.get(expected['owner'])
                if current is None or current.model_dump(mode='json') != expected:
                    return 0
                state.permits.pop(current.owner)
                state.completed += 1
                return 1
            settled = Governor.change(group, settle)
            from src.common.logging import log
            log.system.info('event=datasource_mysql_session_reconciled group=%s owner=%s audit_record_id=%s '
                            'settled=%s business_result_confirmed=false', group, expected['owner'], record.id, settled)
            return settled
        except Exception as error:
            from src.common.logging import log
            log.system.warning('event=datasource_mysql_session_recovery_deferred group=%s '
                               'owner=%s exception_type=%s action=retain_unknown_and_retry_probe',
                               group, expected['owner'], type(error).__name__)
            return 0
        finally:
            def relinquish(state, now):
                if state.recovery_owner == nonce:
                    state.recovery_owner, state.recovery_until = None, 0
            Governor.change(group, relinquish)

    @classmethod
    def tick(cls, after_id=0):
        from src.apps.system.selectors.runtime_kv import RuntimeKVSelector
        store = Governor.store()
        with store.control_connection():
            page = store.scan(prefix='group:', after_id=after_id, page_size=10)
            rows = list(RuntimeKVSelector.entries(store.name,
                [row['key'] for row in page['items'] if row['key'].endswith(':control')], using=store.using))
        for row in sorted(rows, key=lambda item: item.id):
            state = Governor.read_state(row.value['data'])
            if not any(value.kind == DatasourcePermitKindEnum.OPERATION or value.mysql_session is not None
                       for value in state.permits.values()):
                continue
            group = row.key.split(':')[1]
            from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService
            recovered = DatasourcePermitReconciliationService.recover_confirmed(group)
            if any(value.mysql_session is not None and (
                    value.state == DatasourcePermitStateEnum.SUSPECT or value.expires_at <= time.time())
                   for value in state.permits.values()):
                recovered += cls.recover_group(group)
            return {'next_cursor': row.id, 'recovered': recovered}
        return {'next_cursor': page['next_cursor'] or 0, 'recovered': 0}

    @classmethod
    def consume(cls, stop_event):
        from django.db import close_old_connections, connections
        from src.common.logging import log
        cursor = 0
        incident_cursor, last_delivery = 0, float('-inf')
        last_warning = float('-inf')
        try:
            while not stop_event.is_set():
                try:
                    close_old_connections()
                    cursor = cls.tick(cursor)['next_cursor']
                    if time.monotonic() - last_delivery >= 5:
                        from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService
                        incident_cursor = DatasourceHealthIncidentService.retry_pending(incident_cursor)
                        last_delivery = time.monotonic()
                except Exception as error:
                    if time.monotonic() - last_warning >= 30:
                        log.system.warning('event=datasource_session_recovery_unavailable exception_type=%s '
                                           'action=retain_unknown_and_retry_probe', type(error).__name__)
                        last_warning = time.monotonic()
                stop_event.wait(1)
        finally:
            connections.close_all()
