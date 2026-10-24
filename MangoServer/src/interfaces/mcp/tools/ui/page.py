from __future__ import annotations

from src.apps.auto_ui.services.page_service import PageService
from .helpers import _ui_service_call
from .helpers import (
    current_user,
)


def register_page_tools(mcp):
    @mcp.tool()
    def search_ui_pages(project_product_id: int | None = None, module_id: int | None = None, keyword: str | None = None,
                        page: int = 1, page_size: int = 10) -> dict:
        """搜索 UI 页面。"""
        return _ui_service_call(PageService.search_pages, project_product_id, module_id, keyword, page, page_size)

    @mcp.tool()
    def get_ui_page_detail(page_id: int) -> dict:
        """查询 UI 页面详情。"""
        return _ui_service_call(PageService.get_page_detail, page_id)

    @mcp.tool()
    def create_ui_page(project_product_id: int, module_id: int, name: str, url: str) -> dict:
        """创建 UI 页面。"""
        user = current_user()
        result = _ui_service_call(PageService.create_page, project_product_id, module_id, name, url, user.id)
        if result.get("success"):
            result["message"] = "UI 页面创建成功"
        return result

    @mcp.tool()
    def update_ui_page(page_id: int, name: str | None = None, url: str | None = None,
                       module_id: int | None = None) -> dict:
        """更新 UI 页面。"""
        user = current_user()
        result = _ui_service_call(PageService.update_page, page_id, user.id, name, url, module_id)
        if result.get("success"):
            result["message"] = "UI 页面更新成功"
        return result
