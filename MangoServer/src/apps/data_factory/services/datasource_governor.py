import hashlib
import json
import os
import random
import socket
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import math
import threading

from django.conf import settings
from django.db import OperationalError, transaction
from pydantic import ValidationError

from src.apps.data_factory.enums.performance import (
    DatasourcePermitKindEnum, DatasourcePermitStateEnum, DatasourceQueueLaneEnum,
)
from src.apps.data_factory.exceptions import (
    DataFactoryError, DATASOURCE_ADMISSION_TIMEOUT, DATASOURCE_GOVERNOR_UNAVAILABLE, DATASOURCE_POLICY_INVALID,
    DATASOURCE_RECONCILIATION_REQUIRED,
    DATASOURCE_SETTLEMENT_FAILED,
)
from src.apps.data_factory.schemas.performance import (
    DatasourceGovernorState, DatasourcePerformancePolicy, DatasourcePermit, DatasourceWaiter,
    DatasourceAdmissionInfo,
)
from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum
from src.apps.system.services.runtime_kv import RuntimeKV
from src.apps.system.services.system_config import SystemConfigService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum

_operation_scope = ContextVar('datasource_operation_permit', default=None)
_policy_scope = ContextVar('datasource_performance_policy', default=None)
_statement_credits = ContextVar('datasource_statement_credits', default=None)


@dataclass
class StatementCredits:
    group: str
    remaining: int


class DatasourceGovernorService:
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
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
        error = DataFactoryError(definition)
        if reason:
            error.msg += '。' + reason
            error.args = (error.msg,)
        DatasourceInfrastructureService.annotate(error, **context)
        DatasourceInfrastructureService.capture(error)
        return error

    @classmethod
    def reset_pending_process(cls):
        # 调用方持有 _closed_lock；子进程不能核销父进程持有的任何名额。
        if cls._closed_pid != os.getpid():
            cls._closed_connections = set()
            cls._pending_releases = set()
            cls._closed_pid = os.getpid()

    @staticmethod
    def policy():
        current = _policy_scope.get()
        if current is not None:
            return current
        try:
            value = SystemConfigService.get('DATASOURCE_PERFORMANCE_POLICY', default={})
            return DatasourceGovernorService.parse_saved_policy(value)
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
                reason = ('旧配置仍包含已移除的实例覆盖或子配额。请停止新执行，等待现有清理完成及连接池回收后，在配置管理中保存统一配置；勿重置未知占用'
                          if isinstance(value, dict) and any(value.get(key) for key in ('instances', 'scopes')) else
                          DatasourceInfrastructureService.validation_reason(error))
            else:
                reason = '配置必须为符合数据源性能策略结构的对象'
            raise DatasourceGovernorService.infrastructure_error(DATASOURCE_POLICY_INVALID, reason=reason) from error
        except Exception as error:
            raise DatasourceGovernorService.infrastructure_error(DATASOURCE_GOVERNOR_UNAVAILABLE) from error

    @staticmethod
    def parse_saved_policy(value):
        # 旧页面会保存空列表；空设置没有改变归组或限额，可在读取时去掉。
        # 非空旧设置不能静默忽略，否则在途操作可能跨新旧归组重复取得配额。
        if isinstance(value, dict):
            value = dict(value)
            for key in ('instances', 'scopes'):
                if key in value and value[key] == []:
                    value.pop(key)
            for key in ('mysql', 'redis', 'elasticsearch'):
                budget = value.get(key)
                if isinstance(budget, dict) and budget.get('concurrency') == 2 and 'cleanup_reserved' not in budget:
                    # 旧的局部配置依赖保留1个清理名额；新默认2不能使合法旧配置失效。
                    value[key] = {**budget, 'cleanup_reserved': 1}
            if 'pool_size' not in value and any(
                    isinstance(value.get(key), dict) and value[key].get('connections') == 3
                    for key in ('mysql', 'redis', 'elasticsearch')):
                value['pool_size'] = 2
        return DatasourcePerformancePolicy.model_validate(value, strict=True)

    @staticmethod
    def read_state(value):
        # 仅剥离已退役的子配额统计，不删除持有者、租约、排队或未知结果记录。
        if isinstance(value, dict):
            value = dict(value)
            value.pop('scopes', None)
            if isinstance(value.get('permits'), dict):
                value['permits'] = {key: {name: data for name, data in permit.items() if name != 'scopes'}
                                    if isinstance(permit, dict) else permit for key, permit in value['permits'].items()}
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
        from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
        source = SqlExecutionAuditService.current_source()
        stage = source.get('source_stage', '')
        if any(value in stage for value in ('cleanup', 'residual')):
            return DatasourceQueueLaneEnum.CLEANUP
        if any(value in stage for value in ('discover', 'schema', 'metadata', 'test_connection', 'network_probe')):
            return DatasourceQueueLaneEnum.METADATA
        if stage == DatasourceAuditStageEnum.STATEMENT.value:
            return DatasourceQueueLaneEnum.METADATA
        return DatasourceQueueLaneEnum.NORMAL

    @classmethod
    def change(cls, group, callback, *, expected_policy=None):
        try:
            def transform(value, now):
                state = cls.read_state(value)
                result = callback(state, now.timestamp())
                return state.model_dump(mode='json'), result
            store = cls.store()
            retries = 0
            while True:
                with store.control_connection():
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
                from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
                # 已释放所有控制库锁后让出线程；不可递归调用同一配额行的续租。
                # 仍检查报告/清理持有者，停止或接管会中断等待；不重放业务 SQL。
                DatasourceWaitService.pause(random.uniform(0.08, 0.16), renew_operation=False)
        except DataFactoryError:
            raise
        except Exception as error:
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
                    from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
                    raise cls.infrastructure_error(DATASOURCE_POLICY_INVALID,
                        reason=DatasourceInfrastructureService.validation_reason(error)) from error
                if current.model_dump(exclude={'cleanup_consumer_threads'}) != expected_policy.model_dump(
                        exclude={'cleanup_consumer_threads'}):
                    # 配置读取与准入之间发生变化时拒绝旧快照，不以旧组/旧限额再次放行。
                    raise cls.infrastructure_error(DATASOURCE_POLICY_INVALID,
                        reason='配置在读取和执行准入之间已改变，本次未使用旧配置放行。请待配置稳定后重新发起未执行的操作')
            yield

    @classmethod
    def transaction_capacity(cls, target):
        policy, budget, group = cls.target_policy(target)
        if group is None:
            return None
        factor = 1 if cls.lane() == DatasourceQueueLaneEnum.CLEANUP else (100 - budget.cleanup_rate_percent) / 100
        return max(1, math.floor(budget.requests_per_second * factor))

    @staticmethod
    def has_capacity(permits, *, kind, lane, budget, policy, rate_only, cost=1):
        active = [value for value in permits if value.kind == kind]
        limit = budget.connections if kind == DatasourcePermitKindEnum.CONNECTION else budget.concurrency
        reserve = policy.pool_size if kind == DatasourcePermitKindEnum.CONNECTION else budget.cleanup_reserved
        capacity = rate_only or (sum(value.slots for value in active) + cost <= limit and (
            lane == DatasourceQueueLaneEnum.CLEANUP
            or sum(value.slots for value in active if value.lane != DatasourceQueueLaneEnum.CLEANUP)
            + cost <= limit - reserve))
        if kind == DatasourcePermitKindEnum.OPERATION:
            # 连接容量只限制新连接，不阻止已有连接完成操作并归还，缩容时自然排空。
            if not rate_only and lane == DatasourceQueueLaneEnum.METADATA:
                capacity = capacity and not any(value.lane == lane for value in active)
        return capacity

    @staticmethod
    def outcome_unknown(error):
        from urllib.error import HTTPError
        from src.apps.data_factory.exceptions import DATASOURCE_AUDIT_COMPLETION_FAILED
        seen = set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            if getattr(error, '_datasource_outcome_unknown', False):
                return True
            if isinstance(error, HTTPError):
                return error.code >= 500
            number = error.args[0] if getattr(error, 'args', None) else None
            if number in (2006, 2013, 2055):
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
    @contextmanager
    def transaction_budget(cls, target, requests):
        policy, budget, group = cls.target_policy(target)
        if group is None:
            yield
            return
        capacity = min(cls.transaction_capacity(target), policy.transaction_statement_budget)
        if requests < 1:
            from src.apps.data_factory.services.datasource_cost import DatasourceCostService
            DatasourceCostService.reject(f'平台计算的事务SQL数量必须至少为1，当前为 {requests}。本次未执行，请管理员检查事务预算计算逻辑，不要调大配额', not_sent=True)
        policy_token = _policy_scope.set(policy)
        started = time.monotonic()
        try:
            reserved = min(requests, capacity)
            # 事务预付速率，不持有并发名额等待连接。并发名额只在物理 SQL 已拿到连接后申请。
            cls.acquire(target, cost=reserved, rate_only=True)
            credits = StatementCredits(group, reserved)
            lane = cls.lane()
            credit_token = _statement_credits.set(credits)
            try:
                from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
                admission = DatasourceAdmissionInfo(
                    instance_group=group, policy_version=cls.digest(policy.model_dump(mode='json')),
                    queue_lane=cls.lane(), admission_wait_ms=round((time.monotonic() - started) * 1000, 2),
                ).model_dump(mode='json')
                with SqlExecutionAuditService.source({**SqlExecutionAuditService.current_source(),
                                                     'performance': admission,
                                                     'transaction_admission_wait_ms': admission['admission_wait_ms']}):
                    yield
            finally:
                _statement_credits.reset(credit_token)
                unused, credits.remaining = credits.remaining, 0
                if unused:
                    cls.return_unused_rate(group, unused, budget, lane)
        finally:
            _policy_scope.reset(policy_token)

    @classmethod
    def return_unused_rate(cls, group, unused, budget, lane):
        # 只尝试一次；提交响应丢失时宁可少返，不能重试而重复增加额度。
        # 控制库只对已回滚的锁冲突重试事务；这里不创建可重复消费的退款任务。
        def refund(value, now):
            state = cls.read_state(value)
            state.tokens = min(budget.requests_per_second, state.tokens + unused)
            if lane != DatasourceQueueLaneEnum.CLEANUP:
                limit = max(1, budget.requests_per_second * (100 - budget.cleanup_rate_percent) / 100)
                state.normal_tokens = min(limit, state.normal_tokens + unused)
            return state.model_dump(mode='json'), None
        try:
            store = cls.store()
            with store.control_connection(), cls.configuration_guard(store.using):
                store.atomic_update(f'group:{group}:control', refund, ttl=None, utc_clock=True)
        except Exception as error:
            # 未发送 SQL 的剩余额度丢弃不影响数据正确性；不能因此覆盖原业务/清理结果。
            from src.common.logging import log
            log.system.warning('event=datasource_unused_rate_return_failed group=%s unused=%s exception_type=%s',
                               group, unused, type(error).__name__)

    @classmethod
    def acquire(cls, target, *, kind=DatasourcePermitKindEnum.OPERATION, wait=True, rate_only=False, cost=1):
        policy, budget, group = cls.target_policy(target)
        if group is None:
            return None
        owner = uuid.uuid4().hex
        lane = cls.lane()
        from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService
        case_owner = DataFactoryCleanupScheduleService.current_owner()
        permit_created = False
        blocked_by_suspect = False
        suspect_count = 0
        queued_at = time.time()

        def claim(state, now):
            nonlocal permit_created, blocked_by_suspect, queued_at, suspect_count
            permit_created = False
            elapsed = max(0, now - state.updated_at)
            normal_rate = budget.requests_per_second * (100 - budget.cleanup_rate_percent) / 100
            state.tokens = min(budget.requests_per_second, state.tokens + elapsed * budget.requests_per_second)
            state.normal_tokens = min(max(1, normal_rate), state.normal_tokens + elapsed * normal_rate)
            state.metadata_tokens = min(budget.metadata_per_second,
                                        state.metadata_tokens + elapsed * budget.metadata_per_second)
            state.updated_at = now
            state.waiters = {key: value for key, value in state.waiters.items() if value.expires_at > now}
            for permit in state.permits.values():
                if permit.expires_at <= now:
                    permit.state = DatasourcePermitStateEnum.SUSPECT
            active = [value for value in state.permits.values() if value.kind == kind]
            capacity_args = dict(kind=kind, lane=lane, budget=budget, policy=policy,
                                 rate_only=rate_only,
                                 cost=cost if kind == DatasourcePermitKindEnum.CONNECTION else 1)
            capacity = cls.has_capacity(list(state.permits.values()), **capacity_args)
            # 仅用于归因，不删除 suspect，也不以假设的容量放行请求。
            blocked_by_suspect = not capacity and cls.has_capacity([
                value for value in state.permits.values() if value.state != DatasourcePermitStateEnum.SUSPECT
            ], **capacity_args)
            suspect_count = sum(value.state == DatasourcePermitStateEnum.SUSPECT for value in active)
            uses_rate = kind == DatasourcePermitKindEnum.OPERATION
            rates_ok = (not uses_rate or (state.tokens >= cost
                        and (lane == DatasourceQueueLaneEnum.CLEANUP or state.normal_tokens >= cost)
                        and (lane != DatasourceQueueLaneEnum.METADATA or rate_only or state.metadata_tokens >= 1)))
            # 同通道 FIFO；不同通道由保留容量保护，不让新请求插队挤掉旧请求。
            older = any(key != owner and value.lane == lane and value.kind == kind
                        for key, value in state.waiters.items())
            if owner in state.waiters:
                mine = state.waiters[owner]
                older = any(key != owner and value.lane == lane and value.kind == kind
                            and value.created_at < mine.created_at
                            for key, value in state.waiters.items())
            if rate_only:
                older = False
            if uses_rate and not rate_only and lane == DatasourceQueueLaneEnum.CLEANUP:
                normal_capacity = (sum(value.lane != DatasourceQueueLaneEnum.CLEANUP for value in active)
                                   < budget.concurrency - budget.cleanup_reserved)
                if normal_capacity and state.normal_tokens >= 1:
                    # 持续清理不能永久抢占普通通道；等待老化后让普通请求先取得空闲份额。
                    older = older or any(value.kind == kind and value.lane == DatasourceQueueLaneEnum.NORMAL
                                         and now - value.created_at >= 1 for value in state.waiters.values())
            if capacity and rates_ok and not older:
                state.waiters.pop(owner, None)
                if uses_rate:
                    state.tokens -= cost
                    if lane != DatasourceQueueLaneEnum.CLEANUP:
                        state.normal_tokens -= cost
                    if lane == DatasourceQueueLaneEnum.METADATA and not rate_only:
                        state.metadata_tokens -= 1
                if not rate_only:
                    permit_created = True
                    state.permits[owner] = DatasourcePermit(
                        owner=owner, process=cls.process_identity(), lane=lane, kind=kind,
                        slots=cost if kind == DatasourcePermitKindEnum.CONNECTION else 1,
                        case_detail_id=case_owner['parent_case_detail_id'] if case_owner else None,
                        case_attempt=case_owner['parent_attempt'] if case_owner else None,
                        expires_at=now + policy.permit_lease_seconds)
                state.admitted += 1
                return True
            state.throttled += 1
            if wait and not rate_only and (owner in state.waiters or len(state.waiters) < policy.max_waiters):
                mine = state.waiters.setdefault(owner, DatasourceWaiter(
                    lane=lane, kind=kind, created_at=now, expires_at=now + policy.queue_timeout_seconds))
                mine.expires_at = now + policy.queue_timeout_seconds
                queued_at = mine.created_at
            return False

        try:
            # 构造协议池失败时维护线程可能尚未启动；下一次准入也必须先对账。
            cls.flush_pending_releases()
            while True:
                from src.apps.data_factory.services.datasource_wait import DatasourceWaitService, DatasourceAdmissionProbeService
                if wait:
                    delay = DatasourceAdmissionProbeService.delay((group, kind.value), owner)
                    if delay > 0:
                        DatasourceWaitService.pause(delay)
                        continue
                if cls.change(group, claim, expected_policy=policy):
                    DatasourceAdmissionProbeService.finished((group, kind.value), owner)
                    return group, owner
                if not wait or blocked_by_suspect:
                    raise cls.infrastructure_error(
                        DATASOURCE_RECONCILIATION_REQUIRED if blocked_by_suspect else DATASOURCE_ADMISSION_TIMEOUT,
                        reason=(f'存在 {suspect_count} 项结果未确认的同类占用' if blocked_by_suspect else
                                '本次调用不等待执行名额，未因等待超时退出'), database_id=target.id)
                if kind == DatasourcePermitKindEnum.CONNECTION:
                    cls.relieve_connection_pressure(group)
                DatasourceAdmissionProbeService.congested((group, kind.value), owner, queued_at)
                DatasourceWaitService.pause(random.uniform(0.08, 0.16))
        except BaseException as error:
            from src.apps.data_factory.services.datasource_wait import DatasourceAdmissionProbeService
            DatasourceAdmissionProbeService.finished((group, kind.value), owner)
            from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
            DatasourceInfrastructureService.capture(error)
            error._datasource_not_sent = True
            try:
                # 准入提交响应可能丢失，但尚未返回给调用者，业务回调绝不可能已开始。
                if permit_created:
                    cls.release((group, owner))
                else:
                    cls.change(group, lambda state, now: state.waiters.pop(owner, None))
            except Exception:
                # 精确 owner 的未使用名额保留在本进程待确认集合；不覆盖原错误。
                pass
            raise

    @classmethod
    def connection_pressure(cls, group):
        return cls.change(group, lambda state, now: any(
            waiter.kind == DatasourcePermitKindEnum.CONNECTION and waiter.expires_at > now
            for waiter in state.waiters.values()))

    @classmethod
    def renew_waiting_operation(cls):
        permit = _operation_scope.get()
        if permit is None:
            return
        group, owner = permit
        lease = cls.policy().permit_lease_seconds
        def renew(state, now):
            current = state.permits.get(owner)
            if (current is None or current.state != DatasourcePermitStateEnum.ACTIVE
                    or current.expires_at <= now):
                raise DataFactoryError(DATASOURCE_RECONCILIATION_REQUIRED)
            current.expires_at = now + lease
        cls.change(group, renew)

    @staticmethod
    def relieve_connection_pressure(group):
        from src.apps.data_factory.services.datasource_pool import DatasourcePoolRegistry
        from src.apps.data_factory.services.protocol_pool import ProtocolPoolRegistry
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
            state.waiters.pop(owner, None)
            current = state.permits.get(owner)
            if current is not None:
                if unknown:
                    current.state = DatasourcePermitStateEnum.SUSPECT
                else:
                    state.permits.pop(owner)
                    state.completed += 1
        try:
            cls.change(group, release)
        except Exception as error:
            if not unknown:
                from src.common.logging import log
                with cls._closed_lock:
                    pending = len(cls._pending_releases)
                log.system.debug('event=datasource_permit_release_deferred pending_count=%s', pending)
            raise cls.infrastructure_error(DATASOURCE_SETTLEMENT_FAILED,
                reason=('原操作结果仍待确认，平台标记隔离占用也未成功，请先回查原操作' if unknown else
                        '释放执行名额失败，已保留精确名额待对账；这不等于原操作执行失败'), permit_owner=owner) from error
        if not unknown:
            with cls._closed_lock:
                cls._pending_releases.discard(permit)
            from src.apps.data_factory.services.datasource_wait import DatasourceAdmissionProbeService
            DatasourceAdmissionProbeService.changed(group)

    @classmethod
    def finish_operation(cls, permit, *, unknown=False, failure=None):
        try:
            cls.release(permit, unknown=unknown)
        except Exception as error:
            from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
            DatasourceInfrastructureService.capture(error)
            if failure is None:
                raise
            # 原业务已失败；结算错误不可取代原错误，名额仍保持隔离/待确认，不重放 SQL。
            failure._datasource_settlement_failed = True

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
                state.waiters.pop(owner, None)
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
            log.system.debug('event=datasource_connection_release_deferred pending_count=%s', pending)
            raise cls.infrastructure_error(DATASOURCE_SETTLEMENT_FAILED,
                reason='物理连接已关闭，但平台未能核销连接名额。请管理员检查控制数据库及连接配额记录，不要重放原SQL') from error

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
                        raise cls.infrastructure_error(DATASOURCE_POLICY_INVALID,
                            reason='待释放名额的类型或持有进程不匹配，未释放其他进程的名额。请管理员检查连接配额记录')
                    state.permits.pop(permit[1])
                    state.completed += 1
            cls.change(permit[0], confirm)
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
        lease = cls.policy().permit_lease_seconds
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

    @classmethod
    @contextmanager
    def operation(cls, target, *, physical=False):
        policy = cls.target_policy(target)[0]
        token = _policy_scope.set(policy)
        try:
            with cls._operation(target, physical=physical) as admission:
                if admission is None:
                    yield admission
                else:
                    from src.apps.data_factory.services.sql_execution_audit import SqlExecutionAuditService
                    with SqlExecutionAuditService.source({**SqlExecutionAuditService.current_source(),
                                                         'performance': admission}):
                        yield admission
        finally:
            _policy_scope.reset(token)

    @classmethod
    @contextmanager
    def _operation(cls, target, *, physical=False):
        current = _operation_scope.get()
        _, _, group = cls.target_policy(target)
        if target.db_type == DataSourceTypeEnum.MYSQL.value and not physical:
            # 外层审计/元数据流程尚未取得连接，不能先占操作名额造成连接→操作的资源逆序。
            yield None
            return
        if group is None or (current and current[0] == group and not physical):
            yield None
            return
        credits = _statement_credits.get()
        cost = 1
        if physical and credits is not None and credits.group == group:
            if credits.remaining >= 1:
                cost = 0
        borrowed = bool(current and current[0] == group)
        started = time.monotonic()
        permit = cls.acquire(target, rate_only=borrowed, cost=cost)
        if physical and cost == 0:
            credits.remaining -= 1
        token = _operation_scope.set(permit)
        unknown = False
        failure = None
        try:
            yield DatasourceAdmissionInfo(
                instance_group=group, policy_version=cls.digest(cls.policy().model_dump(mode='json')),
                queue_lane=cls.lane(), admission_wait_ms=round((time.monotonic() - started) * 1000, 2),
            ).model_dump(mode='json')
        except BaseException as error:
            failure = error
            unknown = not isinstance(error, Exception) or cls.outcome_unknown(error)
            if unknown and not borrowed:
                error._datasource_unknown_permit = permit
            raise
        finally:
            _operation_scope.reset(token)
            if not borrowed:
                cls.finish_operation(permit, unknown=unknown, failure=failure)
