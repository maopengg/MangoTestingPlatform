import importlib.util
import platform
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

from src.apps.monitoring.schemas.script_context import MonitoringScriptCapabilities
from src.apps.monitoring.constants import SCRIPT_DEPENDENCIES


class MonitoringScriptCapabilitiesService:
    # 仅探测平台已有的常用依赖，不接受客户端模块名、不执行包导入和安装命令。
    @staticmethod
    @lru_cache(maxsize=1)
    def inspect_local():
        packages = {}
        for module, distribution in SCRIPT_DEPENDENCIES:
            try:
                available = importlib.util.find_spec(module) is not None
            except (ValueError, ImportError, OSError):
                # 探测异常不等于缺包；省略该项，让读取方标记为未确认。
                continue
            if not available:
                packages[module] = None
                continue
            try:
                packages[module] = version(distribution)
            except PackageNotFoundError:
                packages[module] = 'installed-version-unknown'
        return MonitoringScriptCapabilities(python_version=platform.python_version(), packages=packages).model_dump()
