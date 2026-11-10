# -*- coding: utf-8 -*-
"""MangoActuator desktop entry and cross-platform packaging command."""

import argparse
import importlib.util
import json
import os
import plistlib
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


APP_NAME = "芒果执行器"
PROJECT_ROOT = Path(__file__).resolve().parent


def _data_argument(source: Path, destination: str) -> str:
    return f"{source}{os.pathsep}{destination}"


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def build_desktop_executable() -> Path:
    """Build the current platform's standalone desktop executable with PyInstaller."""
    if not _module_available("PyInstaller"):
        raise RuntimeError("当前虚拟环境未安装 PyInstaller，请先安装 requirements/desktop.txt")

    build_root = PROJECT_ROOT / "runtime" / "pyinstaller"
    dist_root = PROJECT_ROOT / "dist"
    build_root.mkdir(parents=True, exist_ok=True)
    dist_root.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--onedir" if sys.platform == "darwin" else "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--log-level",
        "WARN",
        "--distpath",
        str(dist_root),
        "--workpath",
        str(build_root / "work"),
        "--specpath",
        str(build_root),
    ]

    data_files = (
        (PROJECT_ROOT / "assets" / "app_icon.ico", "assets"),
        (PROJECT_ROOT / "assets" / "platform_logo.png", "assets"),
        (PROJECT_ROOT / "src" / "settings" / "settings.json", "src/settings"),
        (PROJECT_ROOT / "config" / "capabilities.lock.json", "config"),
    )
    for source, destination in data_files:
        if not source.exists():
            raise FileNotFoundError(f"打包资源不存在：{source}")
        command.extend(("--add-data", _data_argument(source, destination)))

    uiautomator_spec = importlib.util.find_spec("uiautomator2")
    if uiautomator_spec and uiautomator_spec.origin:
        uiautomator_assets = Path(uiautomator_spec.origin).parent / "assets"
        if uiautomator_assets.exists():
            command.extend(("--add-data", _data_argument(uiautomator_assets, "uiautomator2/assets")))

    for package in ("mangotools", "mangoautomation", "pytest", "playwright"):
        if _module_available(package):
            command.extend(("--collect-all", package))
    if _module_available("allure_pytest"):
        command.extend(("--collect-all", "allure_pytest"))

    hidden_imports = [
        "dulwich.porcelain",
        "email.mime.text",
        "email.mime.base",
        "email.mime.multipart",
        "openai",
    ]
    if sys.platform == "win32":
        hidden_imports.append("pystray._win32")
        windows_icon = PROJECT_ROOT / "assets" / "app_icon.ico"
        if not windows_icon.exists():
            raise FileNotFoundError(f"Windows 应用图标不存在：{windows_icon}")
        command.extend(("--icon", str(windows_icon)))
    elif sys.platform == "darwin":
        hidden_imports.append("pystray._darwin")
        macos_icon = PROJECT_ROOT / "assets" / "app_icon.icns"
        if not macos_icon.exists():
            raise FileNotFoundError(f"macOS 应用图标不存在：{macos_icon}")
        command.extend(("--icon", str(macos_icon)))
        command.extend(("--osx-bundle-identifier", "com.mango.actuator.launcher"))
    else:
        hidden_imports.append("pystray._gtk")
    for module in hidden_imports:
        if _module_available(module.split(".")[0]):
            command.extend(("--hidden-import", module))

    excluded_modules = ["mangoui", "PySide6", "qasync", "shiboken6", "pyqtgraph"]
    if sys.platform == "darwin":
        excluded_modules.extend(("dulwich._diff_tree", "dulwich._objects", "dulwich._pack"))
    excluded_modules.extend(("tkinter", "_tkinter"))
    for module in excluded_modules:
        command.extend(("--exclude-module", module))

    command.extend(("--hidden-import", "flet_desktop", "--copy-metadata", "flet", "--copy-metadata", "flet-desktop"))
    if sys.platform != "darwin":
        command.extend(("--collect-data", "flet_desktop"))
    command.append(str(PROJECT_ROOT / "desktop_main.py"))
    print(f"开始打包 {APP_NAME}：{sys.platform}")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    if sys.platform == "win32":
        artifact = dist_root / f"{APP_NAME}.exe"
    elif sys.platform == "darwin":
        artifact = dist_root / f"{APP_NAME}.app"
    else:
        artifact = dist_root / APP_NAME
    if not artifact.exists():
        raise RuntimeError(f"PyInstaller 已结束，但未找到产物：{artifact}")
    if sys.platform == "darwin":
        _prepare_macos_bundle(artifact)
    print(f"打包完成：{artifact}")
    return artifact


def _prepare_macos_bundle(artifact: Path) -> None:
    import flet_desktop

    helpers = artifact / "Contents" / "Helpers"
    helpers.mkdir(exist_ok=True)
    archive = Path(flet_desktop.__file__).parent / "app" / "flet-macos.tar.gz"
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(helpers, filter="data")
    client = helpers / "Flet.app"
    branded_client = helpers / f"{APP_NAME}.app"
    client.rename(branded_client)
    client_plist = branded_client / "Contents" / "Info.plist"
    metadata = plistlib.loads(client_plist.read_bytes())
    # IconName 会优先读取 Flet 的 Assets.car，覆盖 IconFile 指定的平台 Logo。
    metadata.pop("CFBundleIconName", None)
    metadata.update(CFBundleName=APP_NAME, CFBundleDisplayName=APP_NAME,
                    CFBundleIdentifier="com.mango.actuator.desktop", CFBundleIconFile="MangoAppIcon.icns")
    client_plist.write_bytes(plistlib.dumps(metadata))
    shutil.copy2(PROJECT_ROOT / "assets" / "app_icon.icns",
                 branded_client / "Contents" / "Resources" / "MangoAppIcon.icns")
    _thin_macos_client(branded_client, platform.machine())
    launcher_plist = artifact / "Contents" / "Info.plist"
    metadata = plistlib.loads(launcher_plist.read_bytes())
    metadata["LSUIElement"] = True
    launcher_plist.write_bytes(plistlib.dumps(metadata))
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(artifact)], check=True)


def _thin_macos_client(client: Path, architecture: str) -> None:
    # 官方客户端是 Universal；启动器是单架构，运行时保持同一架构即可。
    fat_headers = {b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca", b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"}
    for binary in client.rglob("*"):
        if binary.is_symlink() or not binary.is_file():
            continue
        with binary.open("rb") as source:
            if source.read(4) not in fat_headers:
                continue
        architectures = subprocess.check_output(["lipo", "-archs", str(binary)], text=True).split()
        if architecture not in architectures:
            raise RuntimeError(f"桌面运行时缺少目标架构 {architecture}：{binary.name}")
        if len(architectures) > 1:
            temporary = binary.with_name(binary.name + ".thin")
            subprocess.run(["lipo", str(binary), "-thin", architecture, "-output", str(temporary)], check=True)
            shutil.copymode(binary, temporary)
            temporary.replace(binary)


def packaged_self_check() -> None:
    """Import the frozen runtime and verify required bundled resources."""
    from src.flet_pages.application import FletActuatorApplication  # noqa: F401
    from src.tools import project_dir

    for relative_path in ("assets/app_icon.ico", "assets/platform_logo.png", "src/settings/settings.json", "config/capabilities.lock.json"):
        if not Path(project_dir.resource_path(relative_path)).exists():
            raise RuntimeError(f"打包资源缺失：{relative_path}")
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        contents = Path(sys.executable).resolve().parents[1]
        if not (contents / "Helpers" / f"{APP_NAME}.app" / "Contents" / "MacOS" / "Flet").is_file():
            raise RuntimeError("打包资源缺失：Flet 桌面运行时")
        client_contents = contents / "Helpers" / f"{APP_NAME}.app" / "Contents"
        metadata = plistlib.loads((client_contents / "Info.plist").read_bytes())
        if metadata.get("CFBundleIconName") or metadata.get("CFBundleIconFile") != "MangoAppIcon.icns":
            raise RuntimeError("打包图标配置错误：桌面运行时未使用测试平台 Logo")
        if not (client_contents / "Resources" / "MangoAppIcon.icns").is_file():
            raise RuntimeError("打包资源缺失：测试平台 Logo")


def _version() -> str:
    resource_root = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    settings_path = resource_root / "src" / "settings" / "settings.json"
    return str(json.loads(settings_path.read_text(encoding="utf-8")).get("version", "dev"))


def _show_duplicate_instance_warning(message: str) -> None:
    """Show a startup warning even though the main Tk window has not been created yet."""
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
        build_desktop_executable()
    elif args.self_check:
        packaged_self_check()
    elif args.version:
        print(f"mango-actuator { _version() }")
    else:
        run_desktop()


if __name__ == "__main__":
    main()
