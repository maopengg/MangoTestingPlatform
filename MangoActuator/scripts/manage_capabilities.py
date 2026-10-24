#!/usr/bin/env python3
import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

ACTUATOR_ROOT = Path(__file__).resolve().parent.parent
if str(ACTUATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ACTUATOR_ROOT))

from src.services.capabilities import CAPABILITY_DEFINITIONS, CapabilityRegistry  # noqa: E402
from src.services.perf.k6_runtime import ensure_k6_available  # noqa: E402
from src.tools import project_dir  # noqa: E402


def _manifest() -> dict:
    return json.loads((ACTUATOR_ROOT / "config" / "capabilities.lock.json").read_text(encoding="utf-8"))


def _write_config(profile: str, capabilities: list[str]) -> None:
    path = Path(project_dir.runtime_path()) / "capabilities.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"profile": profile, "enabled_capabilities": capabilities}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ACTUATOR_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"安装命令失败，退出码：{result.returncode}")


def install(codes: list[str], profile: str) -> None:
    manifest = _manifest()["capabilities"]
    installed_codes = []
    for code in codes:
        definition = manifest[code]
        required_os = definition.get("required_os") or []
        if required_os and platform.system().lower() not in required_os:
            if profile == "full":
                continue
            raise RuntimeError(f"当前操作系统不支持能力：{code}")
        requirements = definition.get("requirements")
        if requirements:
            _run([sys.executable, "-m", "pip", "install", "-r", str(ACTUATOR_ROOT / requirements)])
        if code == "web_ui":
            _run([sys.executable, "-m", "playwright", "install", "chromium"])
        if code == "perf":
            ensure_k6_available()
        installed_codes.append(code)
    _write_config(profile, installed_codes)
    CapabilityRegistry.invalidate()
    print(json.dumps(CapabilityRegistry.report(force=True), ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="芒果执行器能力包管理")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="查看能力清单")
    subparsers.add_parser("doctor", help="执行完整能力检查")
    install_parser = subparsers.add_parser("install", help="安装预设或指定能力")
    install_parser.add_argument("values", nargs="+", help="预设名或能力编码")
    args = parser.parse_args()
    manifest = _manifest()
    if args.command == "list":
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    if args.command == "doctor":
        print(json.dumps(CapabilityRegistry.report(force=True), ensure_ascii=False, indent=2))
        return 0
    profiles = manifest["profiles"]
    if len(args.values) == 1 and args.values[0] in profiles:
        profile = args.values[0]
        codes = profiles[profile]
    else:
        profile = "custom"
        codes = list(dict.fromkeys(args.values))
    unknown = sorted(set(codes) - set(CAPABILITY_DEFINITIONS))
    if unknown:
        parser.error(f"未知能力：{','.join(unknown)}")
    install(codes, profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
