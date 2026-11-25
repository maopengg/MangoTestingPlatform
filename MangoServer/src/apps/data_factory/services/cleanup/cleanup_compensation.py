from django.db import transaction
from django.utils import timezone
from pydantic import ValidationError

from src.apps.data_factory.enums.cleanup_history import ResourceCleanupEventEnum
from src.apps.data_factory.enums.cleanup_resource import EsCleanupModeEnum
from src.apps.data_factory.enums.cleanup import DataFactoryCleanupStatusEnum
from src.apps.data_factory.exceptions import DataFactoryError, DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID
from src.apps.data_factory.models import DataFactoryExecutionItem
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
from src.apps.data_factory.schemas.cleanup_resource import EsCleanupCompensation, EsCleanupLineageRule
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService as History
from src.apps.data_factory.services.cleanup.cleanup_lineage import CleanupLineageService as Lineage
from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService as Resources
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.datasource.elasticsearch import ElasticsearchDatasourceService as ES
from src.apps.data_factory.services.recovery.execution_reconciliation import DataFactoryExecutionReconciliation
from src.apps.system.enums.executor import ExecutorTaskStatusEnum, ExecutorTaskTypeEnum
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector


class FactoryCleanupCompensationService:
    @staticmethod
    def reject(reason):
        raise DataFactoryError(DATA_FACTORY_ES_CLEANUP_CONFIG_INVALID, value=(reason,))

    @classmethod
    def plan(cls, execution_id, request, user):
        """只接受定位映射，不接收调用方提供的租户、文档 ID 或归属行。"""
        if not isinstance(request, dict) or set(request) - {'item_id', 'snapshot_index', 'tenant_lineage', 'reason'}:
            cls.reject('补偿仅接受原明细ID、快照序号、子记录映射及原因，不能改写原目标')
        if type(request.get('item_id')) is not int or type(request.get('snapshot_index', 0)) is not int:
            cls.reject('补偿明细ID及快照序号必须为整数')
        # 入口仍受执行记录菜单及产品范围鉴权；不能单凭已知 item_id 跨执行操作。
        item = DataFactoryQuerySelector.data_factory_execution_item().select_related('execution', 'template').filter(
            id=request['item_id'], execution_id=execution_id).first()
        if item is None:
            cls.reject('原执行中没有该清理明细')
        from src.apps.user.services.authorization.permission import ProjectProductScopeService
        if not ProjectProductScopeService.has_project_product(user, item.execution.project_product_id):
            from src.common.exceptions import RESOURCE_ACCESS_DENIED
            raise DataFactoryError(RESOURCE_ACCESS_DENIED)
        if not DataFactoryExecutionReconciliation.owner_ended(item.execution):
            cls.reject('原执行尚未确认结束，不能与仍运行的创建操作并行补偿')
        if TaskCenterQuerySelector.executor_tasks().filter(
            task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value, business_id=execution_id,
            status__in=[ExecutorTaskStatusEnum.PENDING.value, ExecutorTaskStatusEnum.RUNNING.value]).exists():
            cls.reject('原执行仍有在途清理任务，请等待其结束后再预览补偿')
        Resources.validate_snapshot(item, persist_lineage=False)
        state = Resources.state(item)
        index = request.get('snapshot_index', 0)
        if not state.sql_cleaned or not 0 <= index < len(state.snapshots):
            cls.reject('必须先确认原SQL已清理，并指定有效的原ES快照')
        original = state.snapshots[index]
        if not original.index_uuid:
            cls.reject('历史执行缺少索引UUID，不能自动接管当前索引')
        try:
            lineage = (EsCleanupLineageRule.model_validate(request['tenant_lineage'])
                       if request.get('tenant_lineage') is not None else original.rule.tenant_lineage)
            probe = original.model_copy(deep=True)
            probe.rule.tenant_lineage = lineage
            probe.lineage_rows = Lineage.rows(item, probe) if lineage is not None else []
            candidate = EsCleanupCompensation(snapshot_index=index,
                snapshot_digest=History.digest(original.model_dump(mode='json')),
                operator_id=user.id, authorized_at=timezone.now().isoformat(),
                reason=request.get('reason', ''), tenant_lineage=lineage, lineage_rows=probe.lineage_rows,
                seq_no=0, primary_term=1)
        except ValidationError as error:
            cls.reject('补偿原因或关联归属映射格式不正确')
        from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
        from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
        from src.apps.data_factory.enums.audit import DatasourceAuditStageEnum
        source = DataFactorySqlExecutionService.build_source_context(
            execution=item.execution, item=item, stage=DatasourceAuditStageEnum.EXTERNAL_CLEANUP.value)
        with SqlExecutionAuditService.source({**source, 'user_id': user.id, 'test_env': original.environment}):
            return cls.inspect_target(execution_id, item, original, probe, candidate)

    @classmethod
    def inspect_target(cls, execution_id, item, original, probe, candidate):
        binding = Resources.resolve_binding(probe.rule.model_copy(update={'mode': EsCleanupModeEnum.DELETE_AND_VERIFY}),
            item.execution.project_product_id, probe.environment)
        target = DatasourceTargetService.resolve(binding)
        if ES.resolve_index(target, original.requested_index or original.index) != (original.index, original.index_uuid):
            cls.reject('原索引或UUID已变化，补偿停止')
        document = None
        for realtime in (True, False):
            value = ES.document(target, probe.index, probe.document_id, realtime=realtime,
                tenant_path=Resources.source_paths(probe))
            if value is None:
                cls.reject('精确文档当前不存在或视图不一致，请先按原规则重试验证，不授权猜测删除')
            Resources.check_owner(value, probe)
            if document is not None and (document.get('_seq_no'), document.get('_primary_term')) != (
                    value.get('_seq_no'), value.get('_primary_term')):
                cls.reject('预览期间文档版本变化，请重新核查')
            document = value
        if (type(document.get('_seq_no')) is not int or document['_seq_no'] < 0
                or type(document.get('_primary_term')) is not int or document['_primary_term'] < 1):
            cls.reject('文档缺少条件删除版本')
        candidate.seq_no, candidate.primary_term = document['_seq_no'], document['_primary_term']
        candidate = EsCleanupCompensation.model_validate(candidate.model_dump())
        # 授权时间不影响目标摘要；执行时重做全部核验并比较当前版本。
        stable = candidate.model_dump(mode='json', exclude={'authorized_at'})
        digest = History.digest({'execution_id': execution_id, 'item_id': item.id, 'compensation': stable})
        return item, candidate, digest

    @classmethod
    def authorize(cls, execution_id, request, user, expected_digest):
        # 网络核验在控制库事务外完成；落库时只锁归属记录并比较完整原状态。
        item, candidate, digest = cls.plan(execution_id, request, user)
        if digest != expected_digest:
            cls.reject('补偿目标、归属证据或文档版本与预览不一致，请重新预览确认')
        with transaction.atomic():
            execution = CleanupPersistenceService.lock_execution(execution_id)
            locked = DataFactoryExecutionItem.objects.select_for_update().get(id=request['item_id'], execution_id=execution_id)
            if locked.cleanup_resources != item.cleanup_resources or locked.data != item.data:
                cls.reject('核验后执行明细已变化，请重新预览')
            if TaskCenterQuerySelector.executor_tasks().filter(
                    task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value, business_id=execution_id,
                    status__in=[ExecutorTaskStatusEnum.PENDING.value, ExecutorTaskStatusEnum.RUNNING.value]).exists():
                cls.reject('核验后已有新清理任务，请等待其结束')
            state = Resources.state(item)
            state.compensations = [value for value in state.compensations
                                   if value.snapshot_index != candidate.snapshot_index] + [candidate]
            History.append(ResourceCleanupEventEnum.COMPENSATION_AUTHORIZED, item=item, operator_id=user.id,
                authorization_digest=digest, snapshot_digest=candidate.snapshot_digest, compensation=candidate)
            # 旧成功结果归档于授权事件，不能抵扣本次补偿；仅重新打开指定 ES 资源，SQL 保持已核验。
            state.results = [value for value in state.results if value.snapshot_index != candidate.snapshot_index
                and not (value.snapshot_index is None and value.index == state.snapshots[candidate.snapshot_index].index
                         and value.document_id == state.snapshots[candidate.snapshot_index].document_id)]
            state.checkpoints = [value for value in state.checkpoints if value.snapshot_index != candidate.snapshot_index]
            item.cleanup_resources = state.model_dump(mode='json')
            item.cleanup_status = DataFactoryCleanupStatusEnum.NOT_CLEANED.value
            item.cleanup_time = None
            CleanupPersistenceService.save(item, ['cleanup_resources', 'cleanup_status', 'cleanup_time', 'update_time'])
            execution.cleanup_status = DataFactoryCleanupStatusEnum.NOT_CLEANED.value
            execution.cleanup_time = None
            CleanupPersistenceService.save(execution, ['cleanup_status', 'cleanup_time', 'update_time'])
        return digest

    @classmethod
    def confirm(cls, execution_id, request, user, *, preview, preview_token=None, confirm_text=None):
        from src.apps.system.services.coordination.mcp_confirmation import McpConfirmationService
        from src.apps.system.enums.mcp_confirmation import McpConfirmationStatusEnum
        item, candidate, digest = cls.plan(execution_id, request, user)
        action, target = 'data_factory_compensation', f'{execution_id}:{digest}'
        text = f'COMPENSATE_FACTORY_RESOURCE:{item.id}:{candidate.snapshot_index}:{digest[:12]}'
        if preview:
            snapshot = Resources.state(item).snapshots[candidate.snapshot_index]
            return {'preview_token': McpConfirmationService.issue(user.id, action, target, text, 600),
                'confirm_text': text, 'index': snapshot.index, 'document_id': snapshot.document_id,
                'original_mode': snapshot.rule.mode.value, 'effective_mode': EsCleanupModeEnum.DELETE_AND_VERIFY.value,
                'compensation': candidate.model_dump(mode='json'), 'changes_original_snapshot': False}
        status = McpConfirmationService.consume(user.id, action, target, preview_token or '', confirm_text or '')
        if status is not McpConfirmationStatusEnum.ACCEPTED:
            cls.reject('补偿确认无效、已使用或目标版本变化，请重新预览并确认')
        cls.authorize(execution_id, request, user, digest)
        from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
        return DataFactoryCleanup.cleanup_execution(execution_id, force_cleanup=True, allow_missing=True,
            controlled_retry=True, created_by=user.id)
