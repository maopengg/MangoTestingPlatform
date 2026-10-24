import hashlib
import os
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from src.tools import project_dir


K6_VERSION = "2.2.0"
K6_RELEASE_BASE_URL = f"https://github.com/grafana/k6/releases/download/v{K6_VERSION}"
K6_ARCHIVES = {
    ("darwin", "amd64"): (
        f"k6-v{K6_VERSION}-macos-amd64.zip",
        "45a08590511c8a6a9c6331645e60c41624924e848e29472e87c60ac956d50372",
    ),
    ("darwin", "arm64"): (
        f"k6-v{K6_VERSION}-macos-arm64.zip",
        "37a028506bf13578de66c906296803775df28cc2504b1a8c5d786b2803e757c7",
    ),
    ("linux", "amd64"): (
        f"k6-v{K6_VERSION}-linux-amd64.tar.gz",
        "b5a8003c86f35f5cd5ceef1490312c48e587696c94d998cefc6d7b3b4cb1597d",
    ),
    ("linux", "arm64"): (
        f"k6-v{K6_VERSION}-linux-arm64.tar.gz",
        "4ecd64cadcc792402d16293836115480419c4447c032858f564852d98f1bf54c",
    ),
    ("windows", "amd64"): (
        f"k6-v{K6_VERSION}-windows-amd64.zip",
        "ceb2b1e1cf9dbe1303c6c33ec83ffda86dda5c610b4def92064d3c7ebae8d9f4",
    ),
}
_probe_lock = threading.Lock()
_cached_binary: str | None = None
_last_probe_at = 0.0
K6_PROBE_INTERVAL_SECONDS = 10


def _platform_key() -> tuple[str, str] | None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "amd64" if machine in {"x86_64", "amd64"} else machine
    key = (system, architecture)
    return key if key in K6_ARCHIVES else None


def _managed_binary_path() -> Path | None:
    key = _platform_key()
    if not key:
        return None
    executable = "k6.exe" if key[0] == "windows" else "k6"
    return Path(project_dir.runtime_path()) / "bin" / f"k6-v{K6_VERSION}" / executable


def _is_usable(binary: str | Path | None) -> bool:
    if not binary:
        return False
    path = Path(binary).expanduser()
    if not path.is_file() or (os.name != "nt" and not os.access(path, os.X_OK)):
        return False
    try:
        result = subprocess.run(
            [str(path), "version"], capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and "k6" in (result.stdout or result.stderr).lower()


def resolve_k6_binary() -> str | None:
    global _cached_binary, _last_probe_at
    with _probe_lock:
        if _cached_binary and Path(_cached_binary).is_file():
            return _cached_binary
        now = time.monotonic()
        if now - _last_probe_at < K6_PROBE_INTERVAL_SECONDS:
            return None
        _last_probe_at = now
        explicit = os.getenv("MANGO_K6_BINARY")
        candidates = [explicit, _managed_binary_path(), shutil.which("k6")]
        for candidate in candidates:
            if _is_usable(candidate):
                _cached_binary = str(Path(candidate).expanduser().resolve())
                os.environ["MANGO_K6_BINARY"] = _cached_binary
                return _cached_binary
        return None


def _download(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "MangoActuator-k6-bootstrap/1"})
    with urllib.request.urlopen(request, timeout=90) as response, target.open("wb") as output:
        shutil.copyfileobj(response, output)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_binary(archive: Path, target: Path) -> None:
    executable_name = target.name
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as bundle:
            members = [item for item in bundle.infolist() if Path(item.filename).name == executable_name]
            if len(members) != 1:
                raise RuntimeError("k6 安装包中未找到唯一的执行文件")
            with bundle.open(members[0]) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    else:
        with tarfile.open(archive, "r:gz") as bundle:
            members = [item for item in bundle.getmembers() if item.isfile() and Path(item.name).name == executable_name]
            if len(members) != 1:
                raise RuntimeError("k6 安装包中未找到唯一的执行文件")
            source = bundle.extractfile(members[0])
            if source is None:
                raise RuntimeError("k6 执行文件读取失败")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    if os.name != "nt":
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def ensure_k6_available() -> str | None:
    global _cached_binary
    binary = resolve_k6_binary()
    if binary:
        return binary
    if str(os.getenv("MANGO_K6_AUTO_INSTALL", "1")).lower() in {"0", "false", "no", "off"}:
        return None
    key = _platform_key()
    target = _managed_binary_path()
    if not key or target is None:
        return None
    archive_name, expected_checksum = K6_ARCHIVES[key]
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mango-k6-install-", dir=str(target.parent.parent)) as directory:
        archive = Path(directory) / archive_name
        extracted = Path(directory) / target.name
        _download(f"{K6_RELEASE_BASE_URL}/{archive_name}", archive)
        actual_checksum = _sha256(archive)
        if actual_checksum != expected_checksum:
            raise RuntimeError(
                f"k6 安装包校验失败：期望 {expected_checksum}，实际 {actual_checksum}"
            )
        _extract_binary(archive, extracted)
        if not _is_usable(extracted):
            raise RuntimeError("k6 安装后可用性校验失败")
        os.replace(extracted, target)
    os.environ["MANGO_K6_BINARY"] = str(target)
    _cached_binary = str(target)
    return str(target)
