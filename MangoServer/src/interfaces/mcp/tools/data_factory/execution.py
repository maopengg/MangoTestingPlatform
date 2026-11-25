from __future__ import annotations

from src.apps.data_factory.enums import DataFactoryCleanupStatusEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.cleanup.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.cleanup.cleanup_compensation import FactoryCleanupCompensationService
from src.apps.data_factory.services.cleanup.cleanup_history import ResourceCleanupHistoryService
from src.apps.data_factory.selectors.cleanup_history import ResourceCleanupHistorySelector
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    validate_dangerous_action_confirmation,
    current_user,
)
from .helpers import _execution_detail, _execution_summary
from .helpers import (
    fail,
    ok,
)


def register_execution_tools(mcp):
    @mcp.tool()
    def list_data_factory_executions(
            project_product_id: int | None = None,
            module_id: int | None = None,
            template_id: int | None = None,
            source_type: int | None = None,
            source_id: int | None = None,
            status: int | None = None,
            cleanup_status: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询数据工厂执行记录。"""
        queryset = DataFactoryQuerySelector.data_factory_execution().select_related("template", "project_product",
                                                                                    "module").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if template_id is not None:
            queryset = queryset.filter(template_id=template_id)
        if source_type is not None:
            queryset = queryset.filter(source_type=source_type)
        if source_id is not None:
            queryset = queryset.filter(source_id=source_id)
        if status is not None:
            queryset = queryset.filter(status=status)
        if cleanup_status is not None:
            queryset = queryset.filter(cleanup_status=cleanup_status)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        return ok(
            {
                "items": [_execution_summary(item) for item in
                          queryset.order_by("-create_time")[offset: offset + page_size]],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def get_data_factory_execution_detail(execution_id: int, history_page: int = 1, history_page_size: int = 10) -> dict:
        """查询执行详情、SQL/ES分资源诊断及追加式清理历史；历史分页默认10条、最多50条，未确认残留不能视为0。"""
        detail = _execution_detail(execution_id)
        detail['cleanup_history'] = ResourceCleanupHistorySelector.for_execution(
            execution_id, page=history_page, page_size=history_page_size)
        return ok(detail)

    @mcp.tool()
    def preview_cleanup_data_factory_execution_impact(execution_id: int, force_cleanup: bool = True,
            compensation: dict | None = None) -> dict:
        """预览原执行的清理影响并生成一次性确认。verify只验证，delete_and_verify条件删除并完整观察。

        历史精确补偿可传compensation={item_id,snapshot_index,reason,tenant_lineage?}；
        仅接受原执行的可证明归属，不接收文档ID、租户或强删开关。平台冻结当前版本，原快照不变。
        展示影响并取得用户授权后，将相同参数及确认凭据传给cleanup_data_factory_execution；不得重跑业务创建。
        """
        detail = _execution_detail(execution_id)
        compensation_plan, digest = None, None
        if compensation is not None:
            _, candidate, digest = FactoryCleanupCompensationService.plan(execution_id, compensation, current_user())
            compensation_plan = candidate.model_dump(mode='json')
        items = detail["items"]
        pending_items = [
            item
            for item in items
            if item.get("cleanup_status") != DataFactoryCleanupStatusEnum.SUCCESS.value
        ]
        impact = {
            "execution": detail["execution"],
            "will_cleanup_item_count": len(pending_items),
            "total_item_count": len(items),
            "items": [
                {
                    "id": item.get("id"),
                    "template_id": item.get("template_id"),
                    "template_name": item.get("template_name"),
                    "database_id": item.get("database_id"),
                    "database_name": item.get("database_name"),
                    "alias": item.get("alias"),
                    "primary_value": item.get("primary_value"),
                    "storage_snapshot": item.get("storage_snapshot"),
                    "cleanup_strategy": item.get("cleanup_strategy"),
                    "cleanup_order": item.get("cleanup_order"),
                    "cleanup_status": item.get("cleanup_status"),
                    "cleanup_resources": item.get("cleanup_resources") or {},
                }
                for item in pending_items
            ],
            "risk": "清理按执行快照处理数据库记录；如保存了关联ES规则，verify会等待回查，delete_and_verify会按精确文档ID、租户及版本条件删除并回查。ES未闭环则整体清理失败并进入待办。",
            "force_cleanup": force_cleanup,
            "compensation": compensation_plan,
            "changes_original_snapshot": False,
        }
        execution_no = detail["execution"].get("execution_no")
        confirm_text = f"CLEANUP_DATA_FACTORY_EXECUTION:{execution_id}:{execution_no}"
        return ok(
            create_dangerous_action_preview("cleanup_data_factory_execution",
                _confirmation_target(detail, force_cleanup, digest), confirm_text, impact),
            "已生成数据工厂清理影响预览",
        )

    @mcp.tool()
    def cleanup_data_factory_execution(
            execution_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
            force_cleanup: bool = True,
            compensation: dict | None = None,
    ) -> dict:
        """仅清理原执行资源，不重新造数。必须先预览并回传相同force_cleanup、compensation、token和确认文本。

        归属证据、目标或ES版本变化时重新预览；不支持跳过租户/版本校验。成功必须完成SQL及ES完整验证，
        已成功明细不重放，失败从原执行恢复，历史错误及授权可在执行详情cleanup_history分页查询。
        """
        detail = _execution_detail(execution_id)
        digest = None
        if compensation is not None:
            _, _, digest = FactoryCleanupCompensationService.plan(execution_id, compensation, current_user())
        confirm_error = validate_dangerous_action_confirmation(
            "cleanup_data_factory_execution",
            _confirmation_target(detail, force_cleanup, digest),
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        if compensation is not None:
            FactoryCleanupCompensationService.authorize(execution_id, compensation, current_user(), digest)
        result = DataFactoryCleanup.cleanup_execution(
            execution_id,
            force_cleanup=force_cleanup,
            allow_missing=True,
            controlled_retry=True,
            created_by=current_user().id,
        )
        if result.get("fail"):
            return fail(
                "数据工厂执行记录清理失败",
                "DATA_FACTORY_CLEANUP_FAILED",
                details=result,
            )
        return ok(result, result.get("message") or "数据工厂执行记录清理完成")


def _confirmation_target(detail, force_cleanup, compensation_digest):
    # 二次确认必须绑定实际规则和明细，不能预览 verify 后改参执行补偿删除。
    identity = {'execution_id': detail['execution']['id'], 'force_cleanup': force_cleanup,
                'compensation_digest': compensation_digest, 'items': [
                    {key: item.get(key) for key in ('id', 'primary_value', 'cleanup_status', 'cleanup_resources')}
                    for item in detail['items']]}
    return f"{detail['execution']['id']}:{ResourceCleanupHistoryService.digest(identity)}"
