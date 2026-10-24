from __future__ import annotations

from .tools import register_functional_test_tools as register_functional_test_domain_tools


def register_functional_test_tools(mcp):
    register_functional_test_domain_tools(mcp)
