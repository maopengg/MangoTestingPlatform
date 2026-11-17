from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum, DatasourcePermitStateEnum
from src.apps.data_factory.exceptions import DATASOURCE_RECONCILIATION_REQUIRED
from src.apps.data_factory.schemas.performance import DatasourcePermitReview, DatasourcePermitReviewReceipt
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor


class DatasourcePermitReconciliationService:
    """运维核查后的精确核销；过期、报告结束、Pod 消失均不是释放证明。"""

    @staticmethod
    def inspect(group):
        return Governor.change(group, lambda state, now: [
            permit.model_dump(mode='json') for permit in state.permits.values()
            if permit.state == DatasourcePermitStateEnum.SUSPECT or permit.expires_at <= now])

    @staticmethod
    def referenced_audit_ids():
        """审计保留期清理不能先删除仍被在途/未知占用引用的恢复证据。"""
        from src.apps.system.selectors.runtime_kv import RuntimeKVSelector
        store = Governor.store()
        ids, requests, cursor = set(), set(), 0
        while True:
            with store.control_connection():
                page = store.scan(prefix='group:', after_id=cursor, page_size=100)
                keys = [row['key'] for row in page['items'] if row['key'].endswith(':control')]
                for row in RuntimeKVSelector.entries(store.name, keys, using=store.using):
                    state = Governor.read_state(row.value['data'])
                    ids.update(permit.audit_record_id for permit in state.permits.values()
                               if permit.audit_record_id is not None)
                    requests.update(permit.audit_request_id for permit in state.permits.values()
                                    if permit.audit_request_id is not None)
            if page['next_cursor'] is None:
                if requests:
                    from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
                    ids.update(record.id for record in ExecutionAuditSelector.request_evidence(requests).values())
                return ids
            cursor = page['next_cursor']

    @classmethod
    def recover_closed_connections(cls, group):
        """只消费物理关闭证明；不依赖旧进程存活，不推断任何 SQL/Case 的结果。"""
        from pydantic import ValidationError
        from src.apps.data_factory.schemas.performance import DatasourceConnectionClosure
        store = Governor.store()
        candidates = Governor.change(group, lambda state, now: [
            permit.model_dump(mode='json') for permit in state.permits.values()
            if permit.kind == DatasourcePermitKindEnum.CONNECTION and permit.created_at is not None])
        verified = []
        for expected in candidates:
            key = f"closed:{group}:{expected['owner']}"
            with store.control_connection():
                raw = store.get(key)
            if raw is None:
                continue
            try:
                proof = DatasourceConnectionClosure.model_validate(raw)
            except ValidationError:
                continue
            if (proof.group == group and proof.owner == expected['owner']
                    and proof.process == expected['process'] and proof.confirmed_at >= expected['created_at']):
                if proof.basis == 'server_session_absent':
                    if (proof.mysql_session.model_dump(mode='json') != expected.get('mysql_session')
                            or expected['state'] == DatasourcePermitStateEnum.ACTIVE.value
                            and expected['expires_at'] > proof.confirmed_at):
                        continue
                verified.append((expected, proof.confirmed_at, proof.basis))
        def settle(state, now):
            settled = []
            for expected, stamp, _basis in verified:
                current = state.permits.get(expected['owner'])
                if current is not None and current.model_dump(mode='json') == expected and stamp <= now:
                    state.permits.pop(current.owner)
                    state.completed += 1
                    settled.append(current)
            return settled
        settled = Governor.change(group, settle) if verified else []
        if settled:
            from src.common.logging import log
            for permit in settled:
                basis = next(basis for value, _, basis in verified if value['owner'] == permit.owner)
                log.system.info('event=datasource_connection_auto_reconciled group=%s owner=%s '
                    'process=%s basis=%s', group, permit.owner, permit.process, basis)
        # 证据不自动过期；仅在已确认 owner 不再占用后删去本项，不能批量清 namespace。
        for expected, _stamp, _basis in verified:
            def discard(state, now):
                if expected['owner'] not in state.permits:
                    store.delete(f"closed:{group}:{expected['owner']}")
            Governor.change(group, discard)
        return len(settled)

    @classmethod
    def recover_confirmed(cls, group):
        """只恢复确知物理操作已终结的名额；不修改业务结果、资源状态或连接名额。"""
        from pydantic import ValidationError
        from src.apps.data_factory.schemas.performance import DatasourceOperationCompletion
        from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
        # 确定结果的结算响应丢失时，原租约可能仍在续期；不能等到过期才发现矛盾。
        candidates = Governor.change(group, lambda state, now: [
            permit.model_dump(mode='json') for permit in state.permits.values()
            if permit.kind == DatasourcePermitKindEnum.OPERATION])
        records = ExecutionAuditSelector.permit_evidence({value['audit_record_id'] for value in candidates
            if value.get('audit_record_id') and value['kind'] == DatasourcePermitKindEnum.OPERATION.value})
        verified = []
        for value in candidates:
            record = records.get(value.get('audit_record_id'))
            if (record is None or record.status not in ('running', 'success', 'fail', 'timeout', 'rolled_back')
                    or value['kind'] != DatasourcePermitKindEnum.OPERATION.value
                    or value.get('created_at') is None):
                continue
            evidence = (record.source_detail or {}).get('completed_operation_permits', [])
            if not isinstance(evidence, list) or len(evidence) > 256:
                continue
            for raw in evidence:
                try:
                    proof = DatasourceOperationCompletion.model_validate(raw)
                except ValidationError:
                    continue
                if (proof.group == group and proof.owner == value['owner'] and proof.process == value['process']
                        and proof.confirmed_at >= value['created_at']):
                    # running 的外层审计也可能已持久化某一条物理 SQL 的终结证明；
                    # 只结束该 owner 的操作占用，不宣称外层事务或 Case 已结束。
                    verified.append((value, proof.confirmed_at))
                    break
        if not verified:
            return 0

        def settle(state, now):
            confirmed = []
            for expected, confirmed_at in verified:
                permit = state.permits.get(expected['owner'])
                # 并发续期、接管或新快照均要求重新核查；不会只凭 owner 删除变化后的占用。
                if (permit is not None and permit.model_dump(mode='json') == expected
                        and confirmed_at <= now):
                    state.permits.pop(permit.owner)
                    state.completed += 1
                    confirmed.append(permit)
            return confirmed
        confirmed = Governor.change(group, settle)
        if confirmed:
            from src.common.logging import log
            for permit in confirmed:
                record = records[permit.audit_record_id]
                log.system.info('event=datasource_permit_auto_reconciled group=%s owner=%s kind=%s '
                    'request_id=%s audit_record_id=%s database_id=%s process=%s basis=confirmed_operation',
                    group, permit.owner, permit.kind.value, record.request_id, permit.audit_record_id,
                    record.database_id, permit.process)
        return len(confirmed)

    @classmethod
    def monitor(cls, *, after_id=0, page_size=100, recover=False):
        """有界扫描，保留未知占用并输出可操作定位；不访问业务数据源。"""
        from src.common.logging import log
        store = Governor.store()
        with store.control_connection():
            page = store.scan(prefix='group:', after_id=after_id, page_size=page_size)
        groups = []
        errors = []
        recovered = 0
        for row in page['items']:
            key = row['key']
            parts = key.split(':')
            if len(parts) != 3 or parts[2] != 'control':
                continue
            group = parts[1]
            def snapshot(state, now):
                unknown = [permit for permit in state.permits.values()
                    if permit.state == DatasourcePermitStateEnum.SUSPECT or permit.expires_at <= now]
                operations = [permit for permit in state.permits.values()
                              if permit.kind == DatasourcePermitKindEnum.OPERATION]
                return {'group': group, 'active_count': len(state.permits) - len(unknown),
                    'suspect_count': len(unknown), 'connection_waiting': state.connection_wait_until > now,
                    'oldest_unknown_seconds': round(max((max(0, now - (value.unknown_since or value.expires_at))
                        for value in unknown), default=0), 2),
                    'oldest_wait_seconds': round(max(0, now - state.connection_wait_since), 2)
                        if state.connection_wait_until > now else 0,
                    'permits': [value.model_dump(mode='json') for value in unknown],
                    'operation_permits': [value.model_dump(mode='json') for value in operations]}
            try:
                if recover:
                    recovered += cls.recover_closed_connections(group)
                    recovered += cls.recover_confirmed(group)
                result = Governor.change(group, snapshot)
            except Exception as error:
                errors.append({'group': group, 'exception_type': type(error).__name__})
                log.system.error('event=datasource_monitor_group_failed group=%s exception_type=%s '
                    'action=inspect_control_state', group, type(error).__name__)
                continue
            groups.append(result)
            if result['oldest_wait_seconds'] >= 30:
                log.system.warning('event=datasource_connection_wait_long group=%s connection_waiting=%s '
                    'oldest_wait_seconds=%s active_count=%s suspect_count=%s action=inspect_audit_and_permits',
                    group, result['connection_waiting'], result['oldest_wait_seconds'],
                    result['active_count'], result['suspect_count'])
            from src.apps.data_factory.selectors.execution_audit import ExecutionAuditSelector
            audit_lookup_ok = True
            try:
                records = ExecutionAuditSelector.permit_evidence({value['audit_record_id']
                    for value in [*result['operation_permits'], *result['permits']]
                    if value.get('audit_record_id')})
                requests = {value['audit_request_id'] for value in [*result['operation_permits'], *result['permits']]
                            if value.get('audit_request_id')}
                if requests:
                    records.update(ExecutionAuditSelector.request_evidence(requests))
            except Exception as error:
                audit_lookup_ok = False
                records = {}
                errors.append({'group': group, 'exception_type': type(error).__name__})
                log.system.error('event=datasource_monitor_audit_lookup_failed group=%s exception_type=%s',
                                 group, type(error).__name__)
            terminal_audits = []
            for permit in result['operation_permits']:
                record = records.get(permit.get('audit_record_id')) or records.get(permit.get('audit_request_id'))
                if record is not None and record.status in ('success', 'fail', 'timeout', 'rolled_back'):
                    terminal_audits.append(record.id)
                    log.system.error('event=datasource_terminal_audit_occupied group=%s owner=%s '
                        'audit_record_id=%s request_id=%s database_id=%s audit_status=%s '
                        'action=verify_physical_completion_evidence', group, permit['owner'], record.id,
                        record.request_id, record.database_id, record.status)
            if audit_lookup_ok:
                from src.apps.data_factory.services.recovery.health_incident import DatasourceHealthIncidentService
                DatasourceHealthIncidentService.safe_observe(f'datasource:{group}',
                    active=bool(result['suspect_count'] or result['oldest_wait_seconds'] >= 30 or terminal_audits),
                    metrics={'unconfirmed_count': result['suspect_count'],
                        'unsettled_count': len(terminal_audits), 'wait_seconds': result['oldest_wait_seconds'],
                        'audit_ids': terminal_audits[:10], 'detail_ids': list(dict.fromkeys(
                            permit['case_detail_id'] for permit in result['operation_permits']
                            if permit.get('case_detail_id')))[:10]})
            if result['suspect_count']:
                log.system.warning('event=datasource_unresolved_occupancy group=%s suspect_count=%s '
                    'connection_waiting=%s oldest_unknown_seconds=%s action=inspect_datasource_permit', group,
                    result['suspect_count'], result['connection_waiting'], result['oldest_unknown_seconds'])
                for permit in result['permits']:
                    record = records.get(permit.get('audit_record_id')) or records.get(permit.get('audit_request_id'))
                    permit['audit'] = ({'request_id': record.request_id, 'database_id': record.database_id}
                                       if record else None)
                    context = {}
                    if record:
                        detail = record.source_detail or {}
                        context = {key: detail[key] for key in (
                            'case_id', 'case_source_id', 'execution_id', 'execution_item_id', 'template_id',
                        ) if type(detail.get(key)) is int and detail[key] > 0}
                        from src.apps.data_factory.enums.audit import DatasourceAuditSourceEnum, DatasourceAuditStageEnum
                        source_type, source_stage = getattr(record, 'source_type', None), getattr(record, 'source_stage', None)
                        if source_type in {value.value for value in DatasourceAuditSourceEnum}:
                            context['source_type'] = source_type
                        if source_stage in {value.value for value in DatasourceAuditStageEnum}:
                            context['source_stage'] = source_stage
                        if type(getattr(record, 'source_id', None)) is int:
                            context['source_id'] = record.source_id
                        permit['audit']['source'] = context
                    log.system.warning('event=datasource_unresolved_permit group=%s owner=%s kind=%s '
                        'request_id=%s audit_record_id=%s database_id=%s process=%s case_detail_id=%s '
                        'case_attempt=%s context=%s action=verify_original_result_and_cleanup', group, permit['owner'],
                        permit['kind'], getattr(record, 'request_id', None) or permit.get('audit_request_id'), permit.get('audit_record_id'),
                        getattr(record, 'database_id', None),
                        permit['process'], permit.get('case_detail_id'), permit.get('case_attempt'), context)
        return {'groups': groups, 'errors': errors, 'recovered_count': recovered, 'next_cursor': page['next_cursor']}

    @classmethod
    def scheduled_monitor(cls):
        store = Governor.store()
        with store.control_connection():
            cursor = store.get('monitor:cursor') or {'after_id': 0}
        result = cls.monitor(after_id=cursor['after_id'], recover=True)
        with store.control_connection():
            store.set('monitor:cursor', {'after_id': result['next_cursor'] or 0}, ttl=None)
        return {'datasource_reconciled_permits': result['recovered_count'],
                'datasource_monitor_errors': len(result['errors']),
                'datasource_suspect_permits': sum(group['suspect_count'] for group in result['groups']),
                'datasource_connection_wait_groups': sum(group['connection_waiting'] for group in result['groups'])}

    @staticmethod
    def reconcile(review, *, apply=False):
        review = DatasourcePermitReview.model_validate(review)
        expected = review.expected_permit
        # 单独的精确 owner 核查凭据，不能使有界配额行随历史核销次数膨胀。
        review_key = f'review:{review.instance_group}:{expected.owner}'
        def confirm(state, now):
            def reject(reason):
                raise Governor.infrastructure_error(DATASOURCE_RECONCILIATION_REQUIRED, reason=reason)
            store = Governor.store()
            saved_value = store.get(review_key)
            saved = DatasourcePermitReviewReceipt.model_validate(saved_value) if saved_value else None
            if saved:
                if (saved.evidence_sha256 != review.evidence_sha256 or saved.kind != expected.kind
                        or saved.process != expected.process or expected.owner in state.permits):
                    reject('该占用已有其他核查记录，未覆盖原证据')
                return {'reconciled': True, 'already_reconciled': True}
            current = state.permits.get(expected.owner)
            if current is None or current.model_dump() != expected.model_dump():
                reject('待核销占用已变化或不存在，请重新获取快照并核查，未释放任何名额')
            if current.state != DatasourcePermitStateEnum.SUSPECT and current.expires_at > now:
                reject('占用仍在有效期内，不能通过历史占用核查释放')
            if current.kind == DatasourcePermitKindEnum.CONNECTION:
                if not review.physical_connection_closed:
                    reject('必须先核实该占用对应的物理连接已经关闭；进程离线或租约过期不足以证明')
            elif not (review.operation_result_verified and review.cleanup_verified):
                reject('必须先独立核查原操作最终结果，并完成所有关联数据的清理与回查；不能直接重放原操作')
            elif current.case_detail_id is not None:
                from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
                if current.case_attempt is None or not DatasourceInfrastructureService.cleanup_review_ready(
                        current.case_detail_id, current.case_attempt):
                    reject('平台仍有本轮未清理的工厂执行或明细，不能仅凭人工声明核销操作占用')
            if apply:
                state.permits.pop(expected.owner)
                state.completed += 1
                receipt = DatasourcePermitReviewReceipt(
                    reviewed_by=review.reviewed_by, evidence_sha256=review.evidence_sha256,
                    reviewed_at=now, kind=expected.kind, process=expected.process)
                # 与 group 行处于同一个独立控制事务；未知提交响应后可凭 receipt 幂等回读。
                store.set(review_key, receipt.model_dump(mode='json'), ttl=None)
            return {'reconciled': apply, 'ready': True}
        result = Governor.change(review.instance_group, confirm)
        if apply:
            from src.common.logging import log
            log.system.info('event=datasource_permit_review_reconciled group=%s kind=%s already_reconciled=%s',
                            review.instance_group, expected.kind.value, result.get('already_reconciled', False))
        return result
