from __future__ import annotations

from .case import register_case_tools
from .product import register_product_tools
from .schema import register_schema_tools


def register_pytest_tools(mcp):
    register_schema_tools(mcp)
    register_product_tools(mcp)
    register_case_tools(mcp)
