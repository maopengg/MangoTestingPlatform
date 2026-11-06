from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum, DatasourcePermitStateEnum
from src.apps.data_factory.exceptions import DATASOURCE_RECONCILIATION_REQUIRED
from src.apps.data_factory.schemas.performance import DatasourcePermitReview, DatasourcePermitReviewReceipt
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor


class DatasourcePermitReconciliationService:
    """运维核查后的精确核销；过期、报告结束、Pod 消失均不是释放证明。"""

    @staticmethod
    def inspect(group):
        return Governor.change(group, lambda state, now: [
            permit.model_dump(mode='json') for permit in state.permits.values()
            if permit.state == DatasourcePermitStateEnum.SUSPECT or permit.expires_at <= now])

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
                from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
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
            from src.apps.data_factory.services.datasource_wait import DatasourceAdmissionProbeService
            DatasourceAdmissionProbeService.changed(review.instance_group)
            from src.common.logging import log
            log.system.info('event=datasource_permit_review_reconciled group=%s kind=%s already_reconciled=%s',
                            review.instance_group, expected.kind.value, result.get('already_reconciled', False))
        return result
