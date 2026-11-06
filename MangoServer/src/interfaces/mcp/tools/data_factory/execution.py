from __future__ import annotations

from src.apps.data_factory.enums import DataFactoryCleanupStatusEnum
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    validate_dangerous_action_confirmation,
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
    def get_data_factory_execution_detail(execution_id: int) -> dict:
        """查询数据工厂执行详情、明细和上下文。"""
        return ok(_execution_detail(execution_id))

    @mcp.tool()
    def preview_cleanup_data_factory_execution_impact(execution_id: int, force_cleanup: bool = True) -> dict:
        """预览清理某次数据工厂执行记录创建数据的影响，并生成二次确认 token。"""
        detail = _execution_detail(execution_id)
        items = detail["items"]
        pending_items = [
            item
            for item in items
            if force_cleanup or item.get("cleanup_status") != DataFactoryCleanupStatusEnum.SUCCESS.value
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
        }
        execution_no = detail["execution"].get("execution_no")
        confirm_text = f"CLEANUP_DATA_FACTORY_EXECUTION:{execution_id}:{execution_no}"
        return ok(
            create_dangerous_action_preview("cleanup_data_factory_execution", execution_id, confirm_text, impact),
            "已生成数据工厂清理影响预览",
        )

    @mcp.tool()
    def cleanup_data_factory_execution(
            execution_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
            force_cleanup: bool = True,
    ) -> dict:
        """清理某次数据工厂执行记录创建的数据。必须先调用 preview_cleanup_data_factory_execution_impact。"""
        confirm_error = validate_dangerous_action_confirmation(
            "cleanup_data_factory_execution",
            execution_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        result = DataFactoryCleanup.cleanup_execution(
            execution_id,
            force_cleanup=force_cleanup,
            allow_missing=True,
            controlled_retry=True,
        )
        if result.get("fail"):
            return fail(
                "数据工厂执行记录清理失败",
                "DATA_FACTORY_CLEANUP_FAILED",
                details=result,
            )
        return ok(result, result.get("message") or "数据工厂执行记录清理完成")
