"""Prepare an isolated macOS desktop client with the platform identity and login frame."""

import hashlib
import plistlib
import platform
from pathlib import Path
import shutil
import subprocess
import tarfile


def _set_initial_window_size(client: Path):
    nib = client / "Contents/Resources/Base.lproj/MainMenu.nib"
    content = nib.read_bytes()
    original = b"{800, 600}"
    # 相同长度替换原生窗口和内容视图尺寸，保持编译 NIB 的对象偏移与长度不变。
    if not content.startswith(b"NIBArchive") or content.count(original) != 2:
        raise RuntimeError("Flet 原生窗口资源结构已变化，请更新桌面客户端适配")
    nib.write_bytes(content.replace(original, b"{360, 442}"))


def prepare_macos_client(destination: Path, *, app_name: str, project_root: Path,
                         bundle_id="com.mango.actuator.desktop") -> Path:
    import flet_desktop

    helpers = destination
    helpers.mkdir(parents=True, exist_ok=True)
    archive = Path(flet_desktop.__file__).parent / "app" / "flet-macos.tar.gz"
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(helpers, filter="data")
    client = helpers / "Flet.app"
    branded_client = helpers / f"{app_name}.app"
    client.rename(branded_client)
    client_plist = branded_client / "Contents" / "Info.plist"
    metadata = plistlib.loads(client_plist.read_bytes())
    # IconName 会优先读取 Flet 的 Assets.car，覆盖 IconFile 指定的平台 Logo。
    metadata.pop("CFBundleIconName", None)
    metadata.update(CFBundleName=app_name, CFBundleDisplayName=app_name,
                    CFBundleIdentifier=bundle_id, CFBundleIconFile="MangoAppIcon.icns")
    client_plist.write_bytes(plistlib.dumps(metadata))
    shutil.copy2(project_root / "assets" / "app_icon.icns",
                 branded_client / "Contents" / "Resources" / "MangoAppIcon.icns")
    _set_initial_window_size(branded_client)
    _thin_macos_client(branded_client, platform.machine())
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(branded_client)], check=True)
    return branded_client


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


def development_client_directory(*, app_name: str, project_root: Path) -> Path:
    import flet_desktop.version

    icon = project_root / "assets/app_icon.icns"
    fingerprint = hashlib.sha256(icon.read_bytes() + app_name.encode() + b"login-frame-v1").hexdigest()[:12]
    root = project_root / "runtime/desktop" / f"flet-{flet_desktop.version.version}-{platform.machine()}-{fingerprint}"
    client = root / f"{app_name}.app"
    if not client.is_dir():
        import tempfile
        root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="prepare-", dir=root.parent) as temporary:
            prepare_macos_client(Path(temporary), app_name=app_name, project_root=project_root,
                                 bundle_id="com.mango.actuator.development")
            try:
                Path(temporary).rename(root)
            except OSError:
                if not client.is_dir():
                    raise
    return root
