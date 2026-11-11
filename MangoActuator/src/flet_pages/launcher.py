"""Desktop command dispatch and runtime startup."""

import argparse
import json
import os
from pathlib import Path
import sys

from .packaging import APP_NAME, PROJECT_ROOT


def _version() -> str:
    resource_root = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    settings_path = resource_root / "src" / "settings" / "settings.json"
    return str(json.loads(settings_path.read_text(encoding="utf-8")).get("version", "dev"))


def _show_duplicate_instance_warning(message: str) -> None:
    """Show duplicate-instance feedback before the main desktop page exists."""
    try:
        import flet as ft

        def show(page):
            page.title = "芒果执行器已在运行"
            page.add(ft.Text(message))
        ft.app(target=show)
    except Exception:
        print(message, file=sys.stderr)


def run_desktop() -> None:
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        os.environ["FLET_VIEW_PATH"] = str(Path(sys.executable).resolve().parents[1] / "Helpers")
    from src.services.runtime import RuntimeInstanceAlreadyRunning
    from src.flet_pages.application import run_flet_application
    from src.tools.log_collector import log

    try:
        run_flet_application()
    except RuntimeInstanceAlreadyRunning as error:
        log.warning(str(error))
        _show_duplicate_instance_warning(str(error))
    except Exception as error:
        log.error(f"Flet 执行器启动失败：{error}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="芒果执行器桌面入口")
    parser.add_argument("--build", action="store_true", help="使用 PyInstaller 打包当前平台桌面程序")
    parser.add_argument("--self-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="store_true", help="输出执行器版本")
    args = parser.parse_args()
    if args.build:
        from .packaging import build_desktop_executable
        build_desktop_executable()
    elif args.self_check:
        from .packaging import packaged_self_check
        packaged_self_check()
    elif args.version:
        print(f"mango-actuator { _version() }")
    else:
        run_desktop()
