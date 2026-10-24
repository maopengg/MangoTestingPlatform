from __future__ import annotations

from .helpers import _method_tree_for
from .helpers import (
    ok,
)


def register_method_tools(mcp):
    @mcp.tool()
    def get_ui_operation_methods(page_type: int | None = None) -> dict:
        """查询 UI 操作方法树。page_type 传 DriveTypeEnum。"""
        return ok({"items": _method_tree_for("operation", page_type)})

    @mcp.tool()
    def get_ui_assertion_methods(page_type: int | None = None) -> dict:
        """查询 UI 断言方法树。page_type 传 DriveTypeEnum。"""
        return ok({"items": _method_tree_for("assertion", page_type)})

    @mcp.tool()
    def get_ui_public_assertion_methods() -> dict:
        """查询 UI 公共断言方法树。"""
        return ok({"items": _method_tree_for("public_assertion")})
