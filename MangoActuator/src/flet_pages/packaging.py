"""Desktop build, bundle resources and packaged self-check."""

import importlib.util
import os
import plistlib
from pathlib import Path
import subprocess
import sys



def _data_argument(source: Path, destination: str) -> str:
    return f"{source}{os.pathsep}{destination}"


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def build_desktop_executable(*, app_name: str, project_root: Path) -> Path:
    """Build the current platform's standalone desktop executable with PyInstaller."""
    if not _module_available("PyInstaller"):
        raise RuntimeError("当前虚拟环境未安装 PyInstaller，请先安装 requirements/desktop.txt")

    build_root = project_root / "runtime" / "pyinstaller"
    dist_root = project_root / "dist"
    build_root.mkdir(parents=True, exist_ok=True)
    dist_root.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        app_name,
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
        (project_root / "assets" / "app_icon.ico", "assets"),
        (project_root / "assets" / "platform_logo.png", "assets"),
        (project_root / "src" / "settings" / "settings.json", "src/settings"),
        (project_root / "config" / "capabilities.lock.json", "config"),
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
        windows_icon = project_root / "assets" / "app_icon.ico"
        if not windows_icon.exists():
            raise FileNotFoundError(f"Windows 应用图标不存在：{windows_icon}")
        command.extend(("--icon", str(windows_icon)))
    elif sys.platform == "darwin":
        hidden_imports.append("pystray._darwin")
        macos_icon = project_root / "assets" / "app_icon.icns"
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
    command.append(str(project_root / "desktop_main.py"))
    print(f"开始打包 {app_name}：{sys.platform}")
    subprocess.run(command, cwd=project_root, check=True)
    if sys.platform == "win32":
        artifact = dist_root / f"{app_name}.exe"
    elif sys.platform == "darwin":
        artifact = dist_root / f"{app_name}.app"
    else:
        artifact = dist_root / app_name
    if not artifact.exists():
        raise RuntimeError(f"PyInstaller 已结束，但未找到产物：{artifact}")
    if sys.platform == "darwin":
        _prepare_macos_bundle(artifact, app_name=app_name, project_root=project_root)
    print(f"打包完成：{artifact}")
    return artifact


def _prepare_macos_bundle(artifact: Path, *, app_name: str, project_root: Path) -> None:
    from .native_client import prepare_macos_client

    prepare_macos_client(artifact / "Contents/Helpers", app_name=app_name, project_root=project_root)
    launcher_plist = artifact / "Contents" / "Info.plist"
    metadata = plistlib.loads(launcher_plist.read_bytes())
    metadata["LSUIElement"] = True
    launcher_plist.write_bytes(plistlib.dumps(metadata))
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(artifact)], check=True)


def packaged_self_check(*, app_name: str) -> None:
    """Import the frozen runtime and verify required bundled resources."""
    from src.flet_pages.application import FletActuatorApplication  # noqa: F401
    from src.tools import project_dir

    for relative_path in ("assets/app_icon.ico", "assets/platform_logo.png", "src/settings/settings.json", "config/capabilities.lock.json"):
        if not Path(project_dir.resource_path(relative_path)).exists():
            raise RuntimeError(f"打包资源缺失：{relative_path}")
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        contents = Path(sys.executable).resolve().parents[1]
        if not (contents / "Helpers" / f"{app_name}.app" / "Contents" / "MacOS" / "Flet").is_file():
            raise RuntimeError("打包资源缺失：Flet 桌面运行时")
        client_contents = contents / "Helpers" / f"{app_name}.app" / "Contents"
        metadata = plistlib.loads((client_contents / "Info.plist").read_bytes())
        if metadata.get("CFBundleIconName") or metadata.get("CFBundleIconFile") != "MangoAppIcon.icns":
            raise RuntimeError("打包图标配置错误：桌面运行时未使用测试平台 Logo")
        if not (client_contents / "Resources" / "MangoAppIcon.icns").is_file():
            raise RuntimeError("打包资源缺失：测试平台 Logo")
