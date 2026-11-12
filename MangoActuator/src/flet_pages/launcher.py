"""Desktop runtime startup and version lookup."""

import json
import os
from pathlib import Path
import sys

def desktop_version(project_root: Path) -> str:
    resource_root = Path(getattr(sys, "_MEIPASS", project_root))
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


def run_desktop(*, app_name: str, project_root: Path) -> None:
    from src.services.runtime import RuntimeInstanceAlreadyRunning
    from src.flet_pages.application import run_flet_application
    from src.tools.log_collector import log

    try:
        if sys.platform == "darwin":
            if getattr(sys, "frozen", False):
                client_directory = Path(sys.executable).resolve().parents[1] / "Helpers"
            else:
                from .native_client import development_client_directory
                client_directory = development_client_directory(app_name=app_name, project_root=project_root)
            os.environ["FLET_VIEW_PATH"] = str(client_directory)
        run_flet_application()
    except RuntimeInstanceAlreadyRunning as error:
        log.warning(str(error))
        _show_duplicate_instance_warning(str(error))
    except Exception as error:
        log.error(f"Flet 执行器启动失败：{error}")
        raise
