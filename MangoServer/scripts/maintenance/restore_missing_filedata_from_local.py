"""Restore missing FileData objects from explicitly supplied local directories.

The default mode is dry-run. Only exact filename matches are eligible for
automatic restoration. When several local copies share a filename, they are
accepted only if their SHA-256 digests are identical.

Usage:
    python scripts/maintenance/restore_missing_filedata_from_local.py --env test \
        /Users/mango/Documents /Users/mango/Downloads /Users/mango/测试文件
    python scripts/maintenance/restore_missing_filedata_from_local.py --env test \
        --execute /Users/mango/Documents /Users/mango/Downloads /Users/mango/测试文件
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path


def find_server_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").exists():
            return parent
    raise RuntimeError("无法定位 MangoServer 目录")


def setup_django(env: str) -> None:
    os.environ.setdefault("DJANGO_ENV", env)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")
    server_dir = find_server_dir()
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    import django

    django.setup()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_local_files(roots: list[Path]) -> dict[str, list[Path]]:
    files_by_name: dict[str, list[Path]] = defaultdict(list)
    for root in roots:
        if not root.is_dir():
            print(f"skip_missing_directory={root}")
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative_parts = path.relative_to(root).parts
            if any(part.startswith(".") for part in relative_parts):
                continue
            files_by_name[path.name].append(path)
    return files_by_name


def collect_missing_objects():
    from django.core.files.storage import default_storage
    from src.apps.system.models import FileData

    objects = defaultdict(list)
    queryset = FileData.objects.exclude(test_file="").exclude(test_file__isnull=True).only(
        "id", "name", "test_file"
    )
    for row in queryset.iterator():
        if not default_storage.exists(row.test_file.name):
            objects[row.test_file.name].append(row)
    return default_storage, objects


def select_candidates(missing_objects, files_by_name):
    selected = []
    conflicts = []
    unmatched = []
    digest_cache: dict[Path, str] = {}

    for object_key, rows in missing_objects.items():
        names = {Path(object_key).name, *(str(row.name or "") for row in rows)}
        candidates = sorted(
            {path for name in names for path in files_by_name.get(name, [])},
            key=lambda path: (len(path.parts), str(path)),
        )
        if not candidates:
            unmatched.append((object_key, rows))
            continue
        digests = set()
        for path in candidates:
            digest_cache.setdefault(path, sha256(path))
            digests.add(digest_cache[path])
        if len(digests) != 1:
            conflicts.append((object_key, rows, candidates))
            continue
        selected.append((object_key, rows, candidates[0], len(candidates)))

    return selected, conflicts, unmatched


def restore(storage, selected) -> tuple[int, list[str]]:
    from django.core.files import File

    restored = 0
    failures = []
    for object_key, _, local_path, _ in selected:
        try:
            with local_path.open("rb") as source:
                saved_name = storage.save(object_key, File(source, name=Path(object_key).name))
            if not storage.exists(object_key):
                failures.append(f"{object_key}: 上传后校验不存在（saved_name={saved_name}）")
                continue
            restored += 1
            print(f"restored={object_key} <- {local_path}")
        except Exception as error:
            failures.append(f"{object_key}: {type(error).__name__}: {error}")
    return restored, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path, help="需要扫描的本地目录")
    parser.add_argument("--env", default="test", help="Django 环境，默认 test")
    parser.add_argument("--execute", action="store_true", help="上传明确匹配的文件")
    args = parser.parse_args()

    setup_django(args.env)
    files_by_name = scan_local_files(args.roots)
    storage, missing_objects = collect_missing_objects()
    selected, conflicts, unmatched = select_candidates(missing_objects, files_by_name)

    print(f"local_files={sum(len(paths) for paths in files_by_name.values())}")
    print(f"missing_rows={sum(len(rows) for rows in missing_objects.values())}")
    print(f"missing_objects={len(missing_objects)}")
    print(f"safe_matches={len(selected)}")
    print(f"conflicts={len(conflicts)}")
    print(f"unmatched={len(unmatched)}")
    for object_key, rows, local_path, copy_count in selected:
        ids = ",".join(str(row.id) for row in rows)
        print(f"safe_match={object_key} <- {local_path} (ids={ids}, identical_copies={copy_count})")
    for object_key, rows, candidates in conflicts:
        ids = ",".join(str(row.id) for row in rows)
        print(f"conflict={object_key} (ids={ids})")
        for candidate in candidates:
            print(f"  candidate={candidate}")

    if not args.execute:
        print("dry_run=true")
        return

    restored, failures = restore(storage, selected)
    print(f"restored_objects={restored}")
    print(f"failed_objects={len(failures)}")
    for failure in failures:
        print(f"failure={failure}")


if __name__ == "__main__":
    main()
