import hashlib
import json
import os
import random
import socket
import time
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings
from django.db import DatabaseError, InterfaceError, OperationalError, transaction
from pydantic import ValidationError

from src.apps.data_factory.enums.performance import (
    DatasourcePermitKindEnum, DatasourcePermitStateEnum, DatasourceQueueLaneEnum,
    DatasourceTimingPhaseEnum as TimingPhase,
)
from src.apps.data_factory.exceptions import (
    DataFactoryError, DATASOURCE_POLICY_INVALID, DATASOURCE_GOVERNOR_UNAVAILABLE,
    DATASOURCE_RECONCILIATION_REQUIRED, DATASOURCE_SETTLEMENT_FAILED,
    DatasourcePolicyRefreshRequired,
)
from src.apps.data_factory.schemas.performance import (
    DatasourceGovernorState, DatasourcePerformancePolicy, DatasourcePermit,
)
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
from src.apps.data_factory.services.governance.datasource_timing import DatasourceTimingService as Timing

_admission_wait = ContextVar('datasource_connection_wait', default=True)


class DatasourceGovernorService:
    """只管理物理连接；历史操作占用只供核查，不再参与新操作准入。"""
    CONNECTION_LEASE_SECONDS = 300
    _closed_lock = threading.RLock()
    _closed_connections = set()
    _pending_releases = set()
    _closed_pid = None

    @staticmethod
    def process_identity():
        from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity
        return f"{socket.gethostname()[:70]}:{os.getpid()}:{RuntimeProcessIdentity.current()['process_token']}"

    @staticmethod
    def infrastructure_error(definition, *, reason=None, **context):
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        error = DataFactoryError(definition)
        if reason:
            error.msg += '。' + reason
            error.args = (error.msg,)
        DatasourceInfrastructureService.annotate(error, **context)
        DatasourceInfrastructureService.capture(error)
        return error

    @classmethod
    def reset_pending_process(cls):
        if cls._closed_pid != os.getpid():
            cls._closed_connections = set()
            cls._pending_releases = set()
            cls._closed_pid = os.getpid()

    @staticmethod
    def parse_saved_policy(value):
        return DatasourcePerformancePolicy.model_validate(value, strict=True)

    @classmethod
    def policy(cls):
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        logged = False
        while True:
            try:
                value = SystemConfigService.get('DATASOURCE_PERFORMANCE_POLICY', default={})
                return cls.parse_saved_policy(value)
            except (DatabaseError, InterfaceError):
                if not logged:
                    from src.common.logging import log
                    log.system.warning('event=datasource_connection_config_wait operation_sent=false')
                    logged = True
                DatasourceWaitService.pause(0.25)
            except (ValidationError, TypeError, ValueError) as error:
                from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
                reason = (DatasourceInfrastructureService.validation_reason(error)
                          if isinstance(error, ValidationError) else '连接配置必须为有效对象')
                if isinstance(value, dict) and value.get('version') == 1:
                    reason = '旧版数据源配置尚未退役，请管理员在维护窗口执行 retire_datasource_limits --apply'
                raise cls.infrastructure_error(DATASOURCE_POLICY_INVALID, reason=reason) from error

    @staticmethod
    def read_state(value):
        return DatasourceGovernorState.model_validate(value or {})

    @classmethod
    def target_policy(cls, target, policy=None):
        kind = {DataSourceTypeEnum.MYSQL.value: 'mysql', DataSourceTypeEnum.REDIS.value: 'redis',
                DataSourceTypeEnum.ELASTICSEARCH.value: 'elasticsearch'}.get(target.db_type)
        if kind is None:
            return None, None, None
        policy = policy or cls.policy()
        return policy, getattr(policy, kind), cls.digest([
            kind, str(target.host).strip().rstrip('.').lower(), int(target.port),
        ])

    @staticmethod
    def digest(value):
        deployment = getattr(settings, 'DATABASES', {}).get('default', {}).get('NAME', '')
        return hashlib.sha256(json.dumps([deployment, value], sort_keys=True).encode()).hexdigest()[:32]

    @staticmethod
    def store():
        return RuntimeKV.namespace(RuntimeKVNamespaceEnum.DATASOURCE_GOVERNOR).independent()

    @staticmethod
    def lane():
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
        stage = SqlExecutionAuditService.current_source().get('source_stage', '')
        if any(value in stage for value in ('cleanup', 'residual')):
            return DatasourceQueueLaneEnum.CLEANUP
        return DatasourceQueueLaneEnum.NORMAL

    @classmethod
    def change(cls, group, callback, *, expected_policy=None, capture_failure=True):
        try:
            def transform(value, now):
                state = cls.read_state(value)
                result = callback(state, now.timestamp())
                return state.model_dump(mode='json'), result
            store = cls.store()
            retries = 0
            while True:
                from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
                with DatasourceWaitService.control_io(), store.control_connection():
                    try:
                        # 配置共享锁与配额行锁属于同一个短事务，必须一起回滚、重新校验。
                        with cls.configuration_guard(store.using, expected_policy):
                            result = store.atomic_update(f'group:{group}:control', transform, ttl=None, utc_clock=True)
                        if retries:
                            from src.common.logging import log
                            log.system.debug('event=datasource_control_lock_recovered group=%s retries=%s', group, retries)
                        return result
                    except OperationalError as error:
                        code = error.args[0] if error.args else None
                        if code not in (1205, 1213):
                            # 断连、读写超时和提交响应丢失都不能假定已回滚。
                            raise
                        store.confirm_control_rollback()
                retries += 1
                if retries == 1:
                    from src.common.logging import log
                    log.system.debug('event=datasource_control_lock_wait group=%s mysql_code=%s', group, code)
                from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
                # 已释放所有控制库锁后让出线程；不可递归调用同一配额行的续租。
                # 仍检查报告/清理持有者，停止或接管会中断等待；不重放业务 SQL。
                with Timing.waiting(TimingPhase.CONTROL_LOCK):
                    DatasourceWaitService.pause(random.uniform(0.08, 0.16))
        except (DataFactoryError, DatasourcePolicyRefreshRequired):
            raise
        except Exception as error:
            if not capture_failure:
                raise
            raise cls.infrastructure_error(DATASOURCE_GOVERNOR_UNAVAILABLE) from error

    @classmethod
    @contextmanager
    def configuration_guard(cls, using, expected_policy=None):
        from src.apps.system.selectors.configuration import ConfigurationSelector
        with transaction.atomic(using=using):
            row = ConfigurationSelector.shared_locked_value('DATASOURCE_PERFORMANCE_POLICY', using)
            if expected_policy is not None:
                try:
                    current = cls.parse_saved_policy(
                        SystemConfigService.cast_value(row[0], row[1], {}) if row is not None else {})
                except ValidationError as error:
                    from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
                    raise cls.infrastructure_error(DATASOURCE_POLICY_INVALID,
                        reason=DatasourceInfrastructureService.validation_reason(error)) from error
                if current.model_dump(exclude={'cleanup_consumer_threads'}) != expected_policy.model_dump(
                        exclude={'cleanup_consumer_threads'}):
                    # 发生在任何配额变换/业务回调之前；退出配置事务后重读，不以旧限额放行。
                    raise DatasourcePolicyRefreshRequired(current)
            yield

    @staticmethod
    def outcome_unknown(error):
        from src.apps.data_factory.services.datasource.data_source_error import DataSourceErrorService
        if getattr(error, '_datasource_operation_not_sent', False):
            return False
        if DataSourceErrorService.confirmed_rejection(error):
            return False
        from urllib.error import HTTPError
        from src.apps.data_factory.exceptions import DATASOURCE_AUDIT_COMPLETION_FAILED
        seen = set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            if getattr(error, '_datasource_outcome_unknown', False):
                return True
            if getattr(error, 'connection_invalidated', False):
                return True
            sqlstate = getattr(error, 'sqlstate', None) or getattr(error, 'pgcode', None)
            if isinstance(sqlstate, str) and (sqlstate.startswith('08') or sqlstate == '40003'):
                return True
            if isinstance(error, HTTPError):
                return error.code == 408 or error.code >= 500
            number = error.args[0] if getattr(error, 'args', None) else None
            if number in (1158, 1159, 1160, 1161, 1184, 2006, 2013, 2014, 2055):
                return True
            if number == 2003 or isinstance(error, (ConnectionRefusedError, socket.gaierror)):
                return False
            name = type(error).__name__
            if name in ('ConnectError', 'ConnectTimeout', 'SSLCertVerificationError', 'CertificateError'):
                return False
            if (isinstance(error, (TimeoutError, OSError)) or 'Timeout' in name or name in
                    ('ConnectionError', 'RemoteProtocolError', 'ProtocolError')
                    or getattr(error, 'code', None) in (
                        DATASOURCE_AUDIT_COMPLETION_FAILED.code, DATASOURCE_SETTLEMENT_FAILED.code)):
                return True
            reason = getattr(error, 'reason', None)
            error = (getattr(error, 'orig', None) or error.__cause__
                     or (reason if isinstance(reason, BaseException) else None))
        return False

    @classmethod
    def acquire(cls, target, *, cost=1, wait=None):
        """只在创建物理连接时申请容量；正常不足或控制库暂不可用时等待。"""
        from src.apps.data_factory.services.governance.datasource_wait import DatasourceWaitService
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService as Audit
        from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
        owner, lane = uuid.uuid4().hex, cls.lane()
        wait = _admission_wait.get() if wait is None else wait
        case_owner = DataFactoryCleanupScheduleService.current_owner()
        record = getattr(Audit.active(), 'record', None)
        started, next_log = time.monotonic(), time.monotonic() + 30
        next_unknown_log = 0
        while True:
            policy, budget, group = cls.target_policy(target)
            if group is None:
                return None
            def claim(state, now):
                used = [value for value in state.permits.values()
                        if value.kind == DatasourcePermitKindEnum.CONNECTION]
                ordinary = sum(value.slots for value in used if value.lane != DatasourceQueueLaneEnum.CLEANUP)
                fits = (sum(value.slots for value in used) + cost <= budget.connections
                        and (lane == DatasourceQueueLaneEnum.CLEANUP
                             or ordinary + cost <= budget.connections - policy.pool_size))
                if not fits:
                    if state.connection_wait_until <= now:
                        state.connection_wait_since = now
                    state.connection_wait_until = max(state.connection_wait_until, now + 2)
                    confirmed = [value for value in used if value.state == DatasourcePermitStateEnum.ACTIVE
                                 and value.expires_at > now]
                    confirmed_normal = sum(value.slots for value in confirmed
                                           if value.lane != DatasourceQueueLaneEnum.CLEANUP)
                    if (sum(value.slots for value in confirmed) + cost <= budget.connections
                            and (lane == DatasourceQueueLaneEnum.CLEANUP
                                 or confirmed_normal + cost <= budget.connections - policy.pool_size)):
                        return 'unconfirmed_connection'
                    return False
                state.permits[owner] = DatasourcePermit(owner=owner, process=cls.process_identity(),
                    lane=lane, kind=DatasourcePermitKindEnum.CONNECTION, slots=cost,
                    created_at=now, expires_at=now + cls.CONNECTION_LEASE_SECONDS,
                    audit_record_id=getattr(record, 'id', None),
                    case_detail_id=case_owner['parent_case_detail_id'] if case_owner else None,
                    case_attempt=case_owner['parent_attempt'] if case_owner else None)
                state.admitted += 1
                return True
            try:
                admitted = cls.change(group, claim, expected_policy=policy, capture_failure=False)
            except DatasourcePolicyRefreshRequired:
                continue
            except (DatabaseError, InterfaceError):
                # 未返回名额前业务连接工厂尚未调用；即使控制事务提交响应丢失也只取消本 owner。
                cls.cancel_unused_connection(group, owner)
                if not wait:
                    raise DataFactoryError(DATASOURCE_GOVERNOR_UNAVAILABLE)
                while (group, owner) in cls._pending_releases:
                    DatasourceWaitService.pause(0.25)
                    cls.cancel_unused_connection(group, owner)
                DatasourceWaitService.pause(0.25)
                continue
            if admitted == 'unconfirmed_connection':
                # 未知连接仍计入预算；尚未建连的请求等待空闲连接回收/独立核查，
                # 不登记成当前 Case 的操作失败，也不接管或重放历史请求。
                if wait and time.monotonic() >= next_unknown_log:
                    from src.common.logging import log
                    log.system.warning('event=datasource_unconfirmed_connection_wait group=%s database_id=%s '
                                       'wait_id=%s operation_sent=false action=await_connection_recovery',
                                       group, target.id, owner)
                    next_unknown_log = time.monotonic() + 30
            if admitted is True:
                return group, owner
            if not wait:
                # 仅限内部恢复探测；正式 Case 不使用“不等待”入口。
                raise DataFactoryError(DATASOURCE_RECONCILIATION_REQUIRED)
            next_log = Timing.diagnose(started, next_log, phase=TimingPhase.CONNECTION_SLOT,
                                       database_id=target.id, wait_id=owner, group=group)
            try:
                cls.relieve_connection_pressure(group)
            except (DatabaseError, InterfaceError):
                pass
            with Timing.waiting(TimingPhase.CONNECTION_SLOT):
                DatasourceWaitService.pause(random.uniform(0.08, 0.16))

    @classmethod
    def cancel_unused_connection(cls, group, owner):
        # acquire 尚未返回给连接工厂；只可撤销本 owner，不表示任何 SQL 已结束。
        with cls._closed_lock:
            cls.reset_pending_process()
            cls._pending_releases.add((group, owner))
        try:
            cls.flush_pending_releases()
        except (DatabaseError, InterfaceError, DataFactoryError):
            from src.common.logging import log
            log.system.warning('event=datasource_unused_connection_settlement_pending group=%s owner=%s', group, owner)

    @classmethod
    def bind_mysql_connection(cls, permit, session, audit_record_id):
        if permit is None:
            return
        def bind(state, now):
            current = state.permits.get(permit[1])
            if (current is None or current.kind != DatasourcePermitKindEnum.CONNECTION
                    or current.process != cls.process_identity()
                    or current.state != DatasourcePermitStateEnum.ACTIVE or current.expires_at <= now):
                raise cls.infrastructure_error(DATASOURCE_RECONCILIATION_REQUIRED)
            current.mysql_session = session
            current.audit_record_id = audit_record_id
        cls.change(permit[0], bind)

    @classmethod
    def connection_pressure(cls, group):
        return cls.change(group, lambda state, now: state.connection_wait_until > now)

    @staticmethod
    def relieve_connection_pressure(group):
        from src.apps.data_factory.services.pool.datasource_pool import DatasourcePoolRegistry
        from src.apps.data_factory.services.pool.protocol_pool import ProtocolPoolRegistry
        DatasourcePoolRegistry.relieve_pressure(group)
        ProtocolPoolRegistry.relieve_pressure(group)

    @classmethod
    def release(cls, permit, *, unknown=False):
        if permit is None:
            return
        group, owner = permit
        if not unknown:
            with cls._closed_lock:
                cls.reset_pending_process()
                cls._pending_releases.add(permit)

        def release(state, now):
            current = state.permits.get(owner)
            if current is not None:
                if unknown:
                    current.state = DatasourcePermitStateEnum.SUSPECT
                    current.unknown_since = current.unknown_since or now
                else:
                    state.permits.pop(owner)
                    state.completed += 1
        try:
            # 由外层附精确 owner 统一登记结算故障；避免同时留下不可定位的准入故障。
            cls.change(group, release, capture_failure=False)
        except Exception as error:
            from src.common.logging import log
            log.system.warning('event=datasource_permit_settlement_failed group=%s owner=%s process=%s '
                               'outcome_unknown=%s exception_type=%s action=inspect_original_audit',
                               group, owner, cls.process_identity(), unknown, type(error).__name__)
            if not unknown:
                with cls._closed_lock:
                    pending = len(cls._pending_releases)
                log.system.debug('event=datasource_permit_release_deferred pending_count=%s', pending)
            raise cls.infrastructure_error(DATASOURCE_SETTLEMENT_FAILED,
                reason=('原操作结果仍待确认，平台标记隔离占用也未成功，请先回查原操作' if unknown else
                        '释放执行名额失败，已保留精确名额待对账；这不等于原操作执行失败'), permit_owner=owner) from error
        if not unknown:
            with cls._closed_lock:
                cls._pending_releases.discard(permit)
        from src.common.logging import log
        log.system.debug('event=datasource_permit_%s group=%s owner=%s process=%s',
                         'suspect' if unknown else 'released', group, owner, cls.process_identity())

    @classmethod
    def finish_connection(cls, permit, *, unknown=False, failure=None, defer_confirmed=False):
        try:
            cls.release(permit, unknown=unknown)
            return True
        except Exception as error:
            from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
            DatasourceInfrastructureService.capture(error)
            if failure is None and not defer_confirmed:
                raise
            # 原业务已失败；结算错误不可取代原错误，名额仍保持隔离/待确认，不重放 SQL。
            if failure is not None:
                failure._datasource_settlement_failed = True
            return False

    @classmethod
    def flush_pending_releases(cls):
        with cls._closed_lock:
            cls.reset_pending_process()
            permits = list(cls._pending_releases)
        for group, owner in permits:
            def confirm(state, now):
                current = state.permits.get(owner)
                if current is not None:
                    # release 也用于 ES 快照回查确认后的跨消费者核销；只确认既有精确 owner，
                    # 不根据过期、进程名或实例组批量释放其他名额。
                    state.permits.pop(owner)
                    state.completed += 1
            cls.change(group, confirm)
            with cls._closed_lock:
                cls._pending_releases.discard((group, owner))
        if permits:
            from src.common.logging import log
            log.system.debug('event=datasource_permit_release_reconciled confirmed_count=%s', len(permits))

    @classmethod
    def connection_closed(cls, permit):
        """仅物理 close 已成功的当前进程持有者可登记；控制面恢复后幂等对账。"""
        cls.connections_closed([permit] if permit is not None else [])

    @classmethod
    def connections_closed(cls, permits):
        if not permits:
            return
        with cls._closed_lock:
            cls.reset_pending_process()
            cls._closed_connections.update(permits)
        try:
            cls.flush_closed_connections(log_recovery=False)
        except Exception as error:
            from src.common.logging import log
            with cls._closed_lock:
                pending = len(cls._closed_connections)
                unconfirmed = list(cls._closed_connections)
            # 控制行结算失败与独立证据写入分离；证据一旦落盘，进程重建也能精确恢复。
            for group, owner in unconfirmed:
                process = cls.process_identity()
                try:
                    from src.apps.data_factory.schemas.performance import DatasourceConnectionClosure
                    store = cls.store()
                    def proof(value, now):
                        if value is not None:
                            saved = DatasourceConnectionClosure.model_validate(value)
                            if (saved.group, saved.owner, saved.process) != (group, owner, process):
                                raise DataFactoryError(DATASOURCE_POLICY_INVALID)
                            return value, None
                        closure = DatasourceConnectionClosure(group=group, owner=owner,
                            process=process, confirmed_at=now.timestamp())
                        return closure.model_dump(mode='json'), None
                    with store.control_connection():
                        store.atomic_update(f'closed:{group}:{owner}', proof, ttl=None, utc_clock=True)
                except Exception as proof_error:
                    # 控制库完全不可用时不能假称已持久化；保留内存并留下可关联的物理关闭证据。
                    log.system.warning('event=datasource_connection_close_proof_pending group=%s owner=%s '
                        'process=%s exception_type=%s action=verify_physical_close_before_reconciliation',
                        group, owner, process, type(proof_error).__name__)
            log.system.debug('event=datasource_connection_release_deferred pending_count=%s', pending)
            log.system.warning('event=datasource_connection_settlement_pending pending_count=%s action=reconcile_close_proof', pending)

    @classmethod
    def flush_closed_connections(cls, *, log_recovery=True):
        with cls._closed_lock:
            cls.reset_pending_process()
            permits = list(cls._closed_connections)
        for permit in permits:
            # 只删除精确 owner，既可处理 suspect，也可处理提交成功但响应丢失后的重复确认。
            def confirm(state, now):
                current = state.permits.get(permit[1])
                if current is not None:
                    if (current.kind != DatasourcePermitKindEnum.CONNECTION
                            or current.process != cls.process_identity()):
                        raise DataFactoryError(DATASOURCE_POLICY_INVALID)
                    state.permits.pop(permit[1])
                    state.completed += 1
            try:
                cls.change(permit[0], confirm, capture_failure=False)
            except DataFactoryError as error:
                if error.code != DATASOURCE_POLICY_INVALID.code:
                    raise
                from src.common.logging import log
                log.system.warning('event=datasource_close_owner_mismatch group=%s owner=%s '
                                   'action=retain_and_review_without_blocking_other_closures', *permit)
                continue
            with cls._closed_lock:
                cls._closed_connections.discard(permit)
        if permits and log_recovery:
            from src.common.logging import log
            with cls._closed_lock:
                pending = len(cls._closed_connections)
            log.system.debug(
                'event=datasource_connection_release_reconciled confirmed_count=%s pending_count=%s',
                len(permits), pending,
            )

    @classmethod
    def renew_connections(cls, permits):
        grouped = {}
        for permit in permits:
            if permit is not None:
                grouped.setdefault(permit[0], set()).add(permit[1])
        lease = cls.CONNECTION_LEASE_SECONDS
        stale = set()
        for group, owners in grouped.items():
            def renew(state, now):
                invalid = set()
                for owner in owners:
                    current = state.permits.get(owner)
                    if current is None or current.kind != DatasourcePermitKindEnum.CONNECTION:
                        invalid.add((group, owner))
                    elif current.state != DatasourcePermitStateEnum.ACTIVE or current.expires_at <= now:
                        current.state = DatasourcePermitStateEnum.SUSPECT
                        invalid.add((group, owner))
                    else:
                        current.expires_at = now + lease
                return invalid
            stale.update(cls.change(group, renew))
        return stale

    @staticmethod
    @contextmanager
    def nonblocking_admission():
        token = _admission_wait.set(False)
        try:
            yield
        finally:
            _admission_wait.reset(token)

    @staticmethod
    def admission_wait_enabled():
        return _admission_wait.get()
