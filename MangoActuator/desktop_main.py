# -*- coding: utf-8 -*-
"""芒果执行器桌面入口。"""

import argparse
from pathlib import Path

from src.flet_pages.launcher import desktop_version, run_desktop


APP_NAME = "芒果执行器"
PROJECT_ROOT = Path(__file__).resolve().parent


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=f"{APP_NAME}桌面入口")
    parser.add_argument("--build", action="store_true", help="使用 PyInstaller 打包当前平台桌面程序")
    parser.add_argument("--self-check", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--version", action="store_true", help="输出执行器版本")
    args = parser.parse_args(argv)
    if args.build:
        from src.flet_pages.packaging import build_desktop_executable
        build_desktop_executable(app_name=APP_NAME, project_root=PROJECT_ROOT)
    elif args.self_check:
        from src.flet_pages.packaging import packaged_self_check
        packaged_self_check(app_name=APP_NAME)
    elif args.version:
        print(f"mango-actuator {desktop_version(PROJECT_ROOT)}")
    else:
        run_desktop(app_name=APP_NAME, project_root=PROJECT_ROOT)


if __name__ == "__main__":
    main()
