from __future__ import annotations

from src.apps.auto_ui.models import Page, PageElement, PageSteps, PageStepsDetailed, UiCase, UiCaseStepsDetailed
from src.apps.auto_ui.selectors.querysets import UiModelQuerySelector
from src.apps.auto_ui.services.assets.asset_deletion import UiAssetDeletionService
from src.interfaces.mcp.common import validate_dangerous_action_confirmation
from .helpers import _delete_preview
from .helpers import (
    fail,
    ok,
)


def register_delete_tools(mcp):
    def _preview_delete(model, item_id: int, action: str, name: str) -> dict:
        item = UiModelQuerySelector.by_id(model, item_id)
        if not item:
            return fail("数据不存在。", "NOT_FOUND")
        return _delete_preview(action, item_id, f"{action.upper()}:{item_id}",
                               {"id": item_id, "name": getattr(item, "name", None), "model": model.__name__})

    def _delete(model, item_id: int, action: str, token: str | None, text: str | None) -> dict:
        error = validate_dangerous_action_confirmation(action, item_id, token, text)
        if error:
            return error
        result = UiAssetDeletionService.delete(model, item_id)
        return ok(result, "删除成功")

    @mcp.tool()
    def preview_delete_ui_page_impact(page_id: int) -> dict:
        return _preview_delete(Page, page_id, "delete_ui_page", "UI 页面")

    @mcp.tool()
    def delete_ui_page(page_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(Page, page_id, "delete_ui_page", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_element_impact(element_id: int) -> dict:
        return _preview_delete(PageElement, element_id, "delete_ui_element", "UI 元素")

    @mcp.tool()
    def delete_ui_element(element_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(PageElement, element_id, "delete_ui_element", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_page_step_impact(page_step_id: int) -> dict:
        return _preview_delete(PageSteps, page_step_id, "delete_ui_page_step", "UI 页面步骤")

    @mcp.tool()
    def delete_ui_page_step(page_step_id: int, preview_token: str | None = None,
                            confirm_text: str | None = None) -> dict:
        return _delete(PageSteps, page_step_id, "delete_ui_page_step", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_page_step_detail_impact(detail_id: int) -> dict:
        return _preview_delete(PageStepsDetailed, detail_id, "delete_ui_page_step_detail", "UI 页面步骤详情")

    @mcp.tool()
    def delete_ui_page_step_detail(detail_id: int, preview_token: str | None = None,
                                   confirm_text: str | None = None) -> dict:
        return _delete(
            PageStepsDetailed,
            detail_id,
            "delete_ui_page_step_detail",
            preview_token,
            confirm_text,
        )

    @mcp.tool()
    def preview_delete_ui_case_impact(case_id: int) -> dict:
        return _preview_delete(UiCase, case_id, "delete_ui_case", "UI case")

    @mcp.tool()
    def delete_ui_case(case_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(UiCase, case_id, "delete_ui_case", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_case_step_impact(case_step_id: int) -> dict:
        return _preview_delete(UiCaseStepsDetailed, case_step_id, "delete_ui_case_step", "UI case step")

    @mcp.tool()
    def delete_ui_case_step(case_step_id: int, preview_token: str | None = None,
                            confirm_text: str | None = None) -> dict:
        return _delete(
            UiCaseStepsDetailed,
            case_step_id,
            "delete_ui_case_step",
            preview_token,
            confirm_text,
        )
