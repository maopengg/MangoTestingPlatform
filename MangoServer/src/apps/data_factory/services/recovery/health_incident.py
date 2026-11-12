"""性能异常的持久状态与通知回执；不参与配额授权，不改变任何业务结果。"""
import hashlib
import json
import uuid

from src.apps.data_factory.schemas.performance import DatasourceHealthIncident, DatasourceHealthMetrics
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor


class DatasourceHealthIncidentService:
    @classmethod
    def observe(cls, scope, *, active, metrics, worker=False, delivery_only=False):
        from src.common.logging import log
        metrics = DatasourceHealthMetrics.model_validate(metrics)
        digest = hashlib.sha256(scope.encode()).hexdigest()[:32]
        key = f'incident:{digest}'
        store, nonce = Governor.store(), uuid.uuid4().hex

        def update(value, now):
            state = DatasourceHealthIncident.model_validate(value or {})
            stamp = now.timestamp()
            state.scope, state.worker = scope, worker
            if not delivery_only:
                state.last_seen_at, state.metrics = stamp, metrics
            if not delivery_only and state.active != active:
                if state.revision == 0:
                    state.generation = stamp
                state.active = active
                state.revision += 1
                if active:
                    state.opened_at, state.resolved_at = stamp, None
                    state.occurrences += 1
                else:
                    state.resolved_at = stamp
            if state.revision > state.delivered_revision and state.publish_until <= stamp:
                state.publisher, state.publish_until = nonce, stamp + 30
                return state.model_dump(mode='json'), state.model_dump(mode='json')
            return state.model_dump(mode='json'), None

        with store.control_connection():
            if not active and store.get(key) is None:
                return None
            pending = store.atomic_update(key, update, ttl=None, utc_clock=True)
        if pending is None:
            return None
        delivered = False
        try:
            from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventService
            from src.common.enums.system_error import SystemErrorEventSource
            # 固定摘要参与指纹；状态及证据写入详情，恢复更新同一事件而非生成无关联的新告警。
            SystemErrorEventService.record_health_transition(revision=pending['revision'], generation=pending['generation'],
                service_name='api-worker' if worker else 'scheduler-service',
                source=SystemErrorEventSource.API_WORKER if worker else SystemErrorEventSource.SCHEDULER,
                request_path=f'datasource-health/{digest}',
                message='执行进展异常，请查看详情中的 active、恢复时间及关联记录',
                trace=json.dumps({**pending, 'status_label': '待排查' if pending['active'] else '已恢复',
                                  'scope': scope, 'worker': worker}, ensure_ascii=False))
            delivered = True
            emit = log.system.warning if pending['active'] else log.system.info
            emit('event=datasource_health_incident_changed scope=%s revision=%s active=%s '
                 'action=inspect_linked_execution_records', scope, pending['revision'], pending['active'])
        finally:
            def receipt(value, now):
                state = DatasourceHealthIncident.model_validate(value)
                if state.publisher == nonce:
                    if delivered:
                        state.delivered_revision = max(state.delivered_revision, pending['revision'])
                    state.publisher, state.publish_until = None, 0
                return state.model_dump(mode='json'), None
            with store.control_connection():
                store.atomic_update(key, receipt, ttl=None, utc_clock=True)
        return pending

    @classmethod
    def retry_pending(cls, after_id=0):
        from src.apps.system.selectors.runtime_kv import RuntimeKVSelector
        store = Governor.store()
        with store.control_connection():
            page = store.scan(prefix='incident:', after_id=after_id, page_size=20)
            rows = list(RuntimeKVSelector.entries(store.name,
                [item['key'] for item in page['items']], using=store.using))
        for row in rows:
            try:
                cls.retry_entry(store, row)
            except Exception as error:
                from src.common.logging import log
                log.system.warning('event=datasource_health_retry_deferred entry_id=%s exception_type=%s '
                                   'action=retain_incident_and_continue', getattr(row, 'id', None), type(error).__name__)
        return page['next_cursor'] or 0

    @classmethod
    def retry_entry(cls, store, row):
        state = DatasourceHealthIncident.model_validate(row.value['data'])
        if state.scope and state.revision > state.delivered_revision:
            cls.observe(state.scope, active=state.active, worker=state.worker,
                        metrics=state.metrics, delivery_only=True)
        elif (not state.active and state.resolved_at is not None
                and row.kv_now.timestamp() - state.resolved_at > 60 * 86400):
            # 闭环状态保留两个月；版本化删除不能删掉并发重新打开的告警或待投递回执。
            with store.control_connection():
                entry = store.get_entry(row.key)
                current = DatasourceHealthIncident.model_validate(entry.value) if entry.found else None
                if (current is not None and not current.active and current.publisher is None
                        and current.delivered_revision == current.revision
                        and current.resolved_at == state.resolved_at):
                    store.delete_if_version(row.key, entry.version)

    @classmethod
    def safe_observe(cls, scope, **kwargs):
        try:
            return cls.observe(scope, **kwargs)
        except Exception as error:
            from src.common.logging import log
            log.system.warning('event=datasource_health_delivery_pending scope=%s exception_type=%s '
                               'action=retry_without_clearing_incident', scope, type(error).__name__)
            return None
