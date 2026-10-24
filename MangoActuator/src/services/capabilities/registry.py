import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.services.capabilities.models import CapabilityDefinition, CapabilityStatus
from src.services.perf.k6_runtime import K6_VERSION, resolve_k6_binary
from src.tools import project_dir


CORE_TASK_TYPES = (
    "executor_command",
    "live_control",
    "config_command",
    "test_control",
)

UI_TASK_TYPES = (
    "element_check",
    "element_deep_check",
    "element_collect",
    "page_scan",
    "page_open",
    "page_step_debug",
    "page_step_node_debug",
    "ui_case",
    "ui_case_step",
    "auth_start",
    "auth_capture",
    "recording",
)

CAPABILITY_DEFINITIONS = {
    "pytest": CapabilityDefinition(
        code="pytest",
        display_name="Pytest",
        supported_os=("linux", "darwin", "windows"),
        task_types=("pytest_execution",),
        default_capacity=5,
    ),
    "web_ui": CapabilityDefinition(
        code="web_ui",
        display_name="Web UI",
        supported_os=("linux", "darwin", "windows"),
        task_types=UI_TASK_TYPES,
        # 实时工作台及元素采集/检测等交互任务共享当前浏览器会话，默认串行处理。
        # UI Case 使用独立 Context，并发容量由 web_parallel 和 UiCaseConcurrency 控制。
        default_capacity=1,
    ),
    "android_ui": CapabilityDefinition(
        code="android_ui",
        display_name="Android UI",
        supported_os=("linux", "darwin", "windows"),
        task_types=UI_TASK_TYPES,
        default_capacity=1,
    ),
    "ios_ui": CapabilityDefinition(
        code="ios_ui",
        display_name="iOS UI",
        supported_os=("darwin",),
        task_types=UI_TASK_TYPES,
        default_capacity=1,
    ),
    "perf": CapabilityDefinition(
        code="perf",
        display_name="性能测试",
        supported_os=("linux", "darwin", "windows"),
        task_types=("perf_execution",),
        default_capacity=1,
    ),
}

PROFILE_CAPABILITIES = {
    "minimal": (),
    "pytest": ("pytest",),
    "standard": ("pytest", "web_ui", "perf"),
    "android": ("pytest", "web_ui", "android_ui", "perf"),
    "full": tuple(CAPABILITY_DEFINITIONS),
    # 兼容旧镜像/环境变量取值；只影响能力选择，不再产生独立核心版本。
    "pytest_web": ("pytest", "web_ui"),
    "web_ui": ("web_ui",),
    "android_ui": ("android_ui",),
    "ios_ui": ("ios_ui",),
}

LEGACY_EXECUTOR_TYPE_CAPABILITIES = {
    "pytest": ("pytest",),
    "pytest_web": ("pytest", "web_ui"),
    "web_ui": ("web_ui",),
    "android_ui": ("android_ui",),
    "ios_ui": ("ios_ui",),
}


class CapabilityRegistry:
    """执行器能力唯一事实源；只暴露完成环境探测后的能力。"""

    CACHE_SECONDS = max(10, int(os.getenv("MANGO_CAPABILITY_CHECK_INTERVAL", "60") or 60))
    _lock = threading.RLock()
    _snapshot: dict[str, CapabilityStatus] = {}
    _checked_monotonic = 0.0
    _running: dict[str, int] = {code: 0 for code in CAPABILITY_DEFINITIONS}

    @classmethod
    def enabled_codes(cls) -> set[str]:
        explicit = os.getenv("MANGO_CAPABILITIES_ENABLED", "").strip()
        if explicit:
            requested = {item.strip() for item in explicit.split(",") if item.strip()}
        else:
            local_config = cls._local_config()
            environment_profile = os.getenv("MANGO_ACTUATOR_PROFILE", "").strip().lower()
            local_capabilities = local_config.get("enabled_capabilities")
            local_profile = str(local_config.get("profile") or "").strip().lower()
            legacy = os.getenv("EXECUTOR_TYPE", "").strip().lower()
            if environment_profile:
                requested = set(PROFILE_CAPABILITIES.get(environment_profile, ()))
            elif isinstance(local_capabilities, list):
                requested = {str(item) for item in local_capabilities}
            elif local_profile:
                requested = set(PROFILE_CAPABILITIES.get(local_profile, ()))
            elif legacy:
                requested = set(LEGACY_EXECUTOR_TYPE_CAPABILITIES.get(legacy, ()))
            else:
                requested = set(PROFILE_CAPABILITIES["standard"])
        return requested & set(CAPABILITY_DEFINITIONS)

    @staticmethod
    def _local_config() -> dict:
        path = Path(project_dir.runtime_path()) / "capabilities.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {}

    @classmethod
    def snapshot(cls, force: bool = False) -> dict[str, CapabilityStatus]:
        now = time.monotonic()
        if not force and cls._snapshot and now - cls._checked_monotonic < cls.CACHE_SECONDS:
            return cls._snapshot.copy()
        with cls._lock:
            now = time.monotonic()
            if not force and cls._snapshot and now - cls._checked_monotonic < cls.CACHE_SECONDS:
                return cls._snapshot.copy()
            enabled = cls.enabled_codes()
            cls._snapshot = {
                code: cls._probe(definition, code in enabled)
                for code, definition in CAPABILITY_DEFINITIONS.items()
            }
            cls._checked_monotonic = time.monotonic()
            return cls._snapshot.copy()

    @classmethod
    def report(cls, force: bool = False) -> list[dict]:
        return [item.to_dict() for item in cls.snapshot(force).values()]

    @classmethod
    def invalidate(cls) -> None:
        with cls._lock:
            cls._checked_monotonic = 0.0
            cls._snapshot = {}

    @classmethod
    def ready(cls, code: str) -> bool:
        status = cls.snapshot().get(str(code))
        return bool(status and status.ready)

    @classmethod
    def supported_task_types(cls) -> list[str]:
        task_types = set(CORE_TASK_TYPES)
        for status in cls.snapshot().values():
            if status.ready:
                task_types.update(CAPABILITY_DEFINITIONS[status.code].task_types)
        return sorted(task_types)

    @classmethod
    def protocol_versions(cls) -> dict[str, int]:
        versions = {task_type: 1 for task_type in CORE_TASK_TYPES}
        for status in cls.snapshot().values():
            if not status.ready:
                continue
            definition = CAPABILITY_DEFINITIONS[status.code]
            versions.update({task_type: definition.protocol_version for task_type in definition.task_types})
        return versions

    @classmethod
    def capability_capacities(cls) -> dict[str, int]:
        """返回能力总容量，供服务端做运行前容量评估。"""
        return {
            code: int(status.capacity)
            for code, status in cls.snapshot().items()
            if status.ready
        }

    @classmethod
    def available_task_type_capacities(cls) -> dict[str, int]:
        """返回当前可立即领取的任务槽位，避免任务领到本地后才因容量不足失败。"""
        snapshot = cls.snapshot()
        perf_exclusive = os.getenv("MANGO_PERF_EXCLUSIVE", "1").strip().lower() not in {
            "0", "false", "no", "off",
        }
        perf_running = cls._running.get("perf", 0) > 0
        other_running = any(
            running > 0 for code, running in cls._running.items() if code != "perf"
        )
        result: dict[str, int] = {}
        for code, status in snapshot.items():
            if not status.ready:
                continue
            available = max(0, int(status.capacity) - cls._running.get(code, 0))
            if perf_exclusive and ((code == "perf" and other_running) or (code != "perf" and perf_running)):
                available = 0
            for task_type in CAPABILITY_DEFINITIONS[code].task_types:
                result[task_type] = result.get(task_type, 0) + available
        if any(
                status.ready
                for code, status in snapshot.items()
                if code in {"web_ui", "android_ui", "ios_ui"}
        ):
            # UI Case 的并发由用户配置的 web_parallel 控制，不能继承 web_ui=1。
            from src.services.ui.case_concurrency import UiCaseConcurrency

            result["ui_case"] = UiCaseConcurrency.available()
        return result

    @classmethod
    def capacity(cls, code: str) -> int:
        status = cls.snapshot().get(code)
        return int(status.capacity) if status and status.ready else 0

    @staticmethod
    def required_capabilities(task_type: str, payload: dict | None = None) -> list[str]:
        payload = payload if isinstance(payload, dict) else {}
        declared = payload.get("required_capabilities")
        if isinstance(declared, list):
            return sorted({str(item) for item in declared if str(item) in CAPABILITY_DEFINITIONS})
        task_type = str(task_type or "")
        if task_type == "perf_execution":
            return ["perf"]
        if task_type == "pytest_execution":
            return ["pytest"]
        func_name = str(payload.get("func_name") or "")
        # 实时画面的启停只管理已有 runtime 的推流协程，不创建或操作浏览器。
        # 允许 stop/start 顺序交叠，避免断线恢复时互相抢占唯一 web_ui 槽位。
        if func_name in {"u_live_stream_start", "u_live_stream_stop"}:
            return []
        if task_type in UI_TASK_TYPES or func_name.startswith("u_"):
            func_args = payload.get("func_args") if isinstance(payload.get("func_args"), dict) else {}
            runtime = CapabilityRegistry._runtime_value(func_args)
            if runtime in {"android", "android_ui", "3"}:
                return ["android_ui"]
            if runtime in {"ios", "ios_ui", "4"}:
                return ["ios_ui"]
            return ["web_ui"]
        return []

    @classmethod
    def acquire(cls, codes: list[str] | tuple[str, ...]) -> bool:
        normalized = sorted(set(codes))
        with cls._lock:
            snapshot = cls.snapshot()
            if any(not snapshot.get(code) or not snapshot[code].ready for code in normalized):
                return False
            perf_exclusive = os.getenv("MANGO_PERF_EXCLUSIVE", "1").strip().lower() not in {
                "0", "false", "no", "off",
            }
            if perf_exclusive:
                if "perf" in normalized and any(
                    running > 0 for code, running in cls._running.items() if code != "perf"
                ):
                    return False
                if "perf" not in normalized and cls._running.get("perf", 0) > 0:
                    return False
            if any(cls._running.get(code, 0) >= snapshot[code].capacity for code in normalized):
                return False
            for code in normalized:
                cls._running[code] = cls._running.get(code, 0) + 1
                snapshot[code].running = cls._running[code]
            return True

    @classmethod
    def release(cls, codes: list[str] | tuple[str, ...]) -> None:
        with cls._lock:
            for code in set(codes):
                cls._running[code] = max(0, cls._running.get(code, 0) - 1)
                if code in cls._snapshot:
                    cls._snapshot[code].running = cls._running[code]

    @classmethod
    def _probe(cls, definition: CapabilityDefinition, enabled: bool) -> CapabilityStatus:
        checked_at = datetime.now(timezone.utc).isoformat()
        if not enabled:
            return CapabilityStatus(
                code=definition.code,
                display_name=definition.display_name,
                state="disabled",
                enabled=False,
                protocol_version=definition.protocol_version,
                capacity=0,
                reason_code="CAPABILITY_DISABLED",
                reason="该能力未启用",
                checked_at=checked_at,
            )
        current_os = platform.system().lower()
        if current_os not in definition.supported_os:
            return CapabilityStatus(
                code=definition.code,
                display_name=definition.display_name,
                state="unavailable",
                enabled=True,
                protocol_version=definition.protocol_version,
                capacity=0,
                reason_code="UNSUPPORTED_OPERATING_SYSTEM",
                reason=f"当前操作系统 {current_os} 不支持该能力",
                checked_at=checked_at,
            )
        probes: dict[str, Callable[[CapabilityDefinition], CapabilityStatus]] = {
            "pytest": cls._probe_pytest,
            "web_ui": cls._probe_web_ui,
            "android_ui": cls._probe_android_ui,
            "ios_ui": cls._probe_ios_ui,
            "perf": cls._probe_perf,
        }
        try:
            status = probes[definition.code](definition)
        except Exception as error:
            status = cls._status_unavailable(definition, "CAPABILITY_PROBE_FAILED", str(error))
        status.enabled = True
        status.checked_at = checked_at
        status.running = cls._running.get(definition.code, 0)
        return status

    @classmethod
    def _probe_pytest(cls, definition: CapabilityDefinition) -> CapabilityStatus:
        try:
            version = importlib.metadata.version("pytest")
        except importlib.metadata.PackageNotFoundError:
            return cls._status_unavailable(definition, "PYTEST_PACKAGE_MISSING", "未安装 pytest")
        result = cls._run([sys.executable, "-m", "pytest", "--version"], timeout=10)
        if result.returncode != 0:
            return cls._status_unavailable(definition, "PYTEST_EXECUTION_FAILED", result.stderr or result.stdout)
        return cls._status_ready(definition, {"pytest": version})

    @classmethod
    def _probe_web_ui(cls, definition: CapabilityDefinition) -> CapabilityStatus:
        try:
            version = importlib.metadata.version("playwright")
        except importlib.metadata.PackageNotFoundError:
            return cls._status_unavailable(definition, "PLAYWRIGHT_PACKAGE_MISSING", "未安装 Playwright")
        browser_ready = bool(os.getenv("PLAYWRIGHT_BROWSERS_PATH") and Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).exists())
        candidate_roots = [
            Path.home() / ".cache" / "ms-playwright",
            Path.home() / "Library" / "Caches" / "ms-playwright",
            Path("/ms-playwright"),
        ]
        browser_ready = browser_ready or any(
            root.exists() and any(item.name.startswith("chromium") for item in root.iterdir())
            for root in candidate_roots if root.exists()
        )
        system_browser = next(
            (
                candidate
                for candidate in (
                    shutil.which("chromium"),
                    shutil.which("chromium-browser"),
                    shutil.which("google-chrome"),
                    shutil.which("chrome"),
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                )
                if candidate and Path(candidate).exists()
            ),
            None,
        )
        browser_ready = browser_ready or bool(system_browser)
        if not browser_ready:
            return cls._status_unavailable(definition, "BROWSER_BINARY_MISSING", "未检测到 Playwright Chromium 浏览器")
        return cls._status_ready(
            definition,
            {"playwright": version, "browser": "chromium"},
            {"browser_binary": system_browser or "playwright-managed"},
        )

    @classmethod
    def _probe_android_ui(cls, definition: CapabilityDefinition) -> CapabilityStatus:
        try:
            appium_version = importlib.metadata.version("Appium-Python-Client")
        except importlib.metadata.PackageNotFoundError:
            return cls._status_unavailable(definition, "APPIUM_PACKAGE_MISSING", "未安装 Appium Python Client")
        adb = shutil.which("adb")
        if not adb:
            return cls._status_unavailable(definition, "ADB_MISSING", "未安装或未配置 adb")
        version_result = cls._run([adb, "version"], timeout=10)
        devices_result = cls._run([adb, "devices"], timeout=10)
        if version_result.returncode != 0 or devices_result.returncode != 0:
            return cls._status_unavailable(definition, "ADB_EXECUTION_FAILED", devices_result.stderr or version_result.stderr)
        devices = [
            line.split("\t", 1)[0]
            for line in devices_result.stdout.splitlines()[1:]
            if "\tdevice" in line
        ]
        if not devices:
            return cls._status_unavailable(
                definition,
                "ANDROID_DEVICE_NOT_FOUND",
                "未检测到已授权且在线的 Android 设备",
                dependencies={"adb": "ready", "devices": []},
            )
        status = cls._status_ready(
            definition,
            {"adb": cls._first_line(version_result.stdout), "appium_client": appium_version},
        )
        status.capacity = len(devices)
        status.dependencies = {"adb": "ready", "devices": devices}
        return status

    @classmethod
    def _probe_ios_ui(cls, definition: CapabilityDefinition) -> CapabilityStatus:
        xcodebuild = shutil.which("xcodebuild")
        if not xcodebuild:
            return cls._status_unavailable(definition, "XCODE_MISSING", "未检测到 Xcode 命令行工具")
        try:
            appium_version = importlib.metadata.version("Appium-Python-Client")
        except importlib.metadata.PackageNotFoundError:
            return cls._status_unavailable(definition, "APPIUM_PACKAGE_MISSING", "未安装 Appium Python Client")
        result = cls._run([xcodebuild, "-version"], timeout=10)
        if result.returncode != 0:
            return cls._status_unavailable(definition, "XCODE_EXECUTION_FAILED", result.stderr or result.stdout)
        return cls._status_ready(
            definition,
            {"xcode": cls._first_line(result.stdout), "appium_client": appium_version},
        )

    @classmethod
    def _probe_perf(cls, definition: CapabilityDefinition) -> CapabilityStatus:
        binary = resolve_k6_binary()
        if not binary:
            return cls._status_unavailable(definition, "K6_MISSING", "未检测到可用的 k6")
        return cls._status_ready(definition, {"k6": K6_VERSION}, {"binary": binary})

    @classmethod
    def _status_ready(
        cls,
        definition: CapabilityDefinition,
        engine_versions: dict[str, str],
        dependencies: dict | None = None,
    ) -> CapabilityStatus:
        capacity = cls._configured_capacity(definition)
        return CapabilityStatus(
            code=definition.code,
            display_name=definition.display_name,
            state="ready",
            enabled=True,
            protocol_version=definition.protocol_version,
            capacity=capacity,
            engine_versions=engine_versions,
            dependencies=dependencies or {},
        )

    @staticmethod
    def _status_unavailable(
        definition: CapabilityDefinition,
        reason_code: str,
        reason: str,
        dependencies: dict | None = None,
    ) -> CapabilityStatus:
        return CapabilityStatus(
            code=definition.code,
            display_name=definition.display_name,
            state="unavailable",
            enabled=True,
            protocol_version=definition.protocol_version,
            capacity=0,
            dependencies=dependencies or {},
            reason_code=reason_code,
            reason=str(reason).strip()[:500] or "能力检查失败",
        )

    @staticmethod
    def _configured_capacity(definition: CapabilityDefinition) -> int:
        key = f"MANGO_CAPACITY_{definition.code.upper()}"
        try:
            return max(1, int(os.getenv(key, str(definition.default_capacity))))
        except (TypeError, ValueError):
            return definition.default_capacity

    @staticmethod
    def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)

    @staticmethod
    def _first_line(value: str) -> str:
        return next((line.strip() for line in value.splitlines() if line.strip()), "unknown")[:120]

    @classmethod
    def _runtime_value(cls, value: object) -> str:
        if not isinstance(value, dict):
            return "web"
        for key in ("runtime_type", "platform", "ui_client_type", "client_type", "type"):
            if key in value and value[key] is not None:
                return str(value[key]).lower()
        for key in ("case", "page", "data", "environment", "project_product"):
            nested = value.get(key)
            if isinstance(nested, dict):
                runtime = cls._runtime_value(nested)
                if runtime != "web":
                    return runtime
        return "web"
