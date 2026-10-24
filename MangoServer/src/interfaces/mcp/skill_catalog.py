from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from django.conf import settings

SKILL_CATALOG_URI = "mango://skills/catalog"
SKILL_RESOURCE_URI_TEMPLATE = "mango://skills/{skill_name}"
SKILL_ROOT_ENV = "MANGO_MCP_SKILL_ROOT"
EXCLUDED_PARTS = {"__pycache__", ".git"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


class McpSkillCatalogService:
    """Publish repository Skills as versioned, read-only MCP content."""

    @classmethod
    def skill_root(cls) -> Path:
        configured = os.getenv(SKILL_ROOT_ENV)
        candidates = []
        if configured:
            candidates.append(Path(configured).expanduser())
        candidates.extend(
            [
                Path(settings.BASE_DIR) / "skill",
                Path(settings.BASE_DIR).parent / "skill",
            ]
        )
        for candidate in candidates:
            root = candidate.resolve()
            if (root / "introductions.json").is_file():
                return root
        raise FileNotFoundError("MCP Skill 目录不存在或缺少 introductions.json")

    @classmethod
    def introductions(cls) -> dict[str, dict[str, Any]]:
        payload = json.loads((cls.skill_root() / "introductions.json").read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("introductions.json 顶层必须是对象")
        return {
            str(name): dict(metadata or {})
            for name, metadata in payload.items()
            if isinstance(metadata, dict)
        }

    @staticmethod
    def _mcp_enabled(metadata: dict[str, Any]) -> bool:
        value = metadata.get("mcp_enabled", True)
        if not isinstance(value, bool):
            raise ValueError("introductions.json 的 mcp_enabled 必须是布尔值")
        return value

    @classmethod
    def mcp_introductions(cls) -> dict[str, dict[str, Any]]:
        return {
            name: metadata
            for name, metadata in cls.introductions().items()
            if cls._mcp_enabled(metadata)
        }

    @staticmethod
    def normalize_skill_name(skill_name: str) -> str:
        normalized = unquote(str(skill_name or '')).partition('#')[0].strip().rstrip('/')
        if not normalized or normalized in {'.', '..'} or '/' in normalized or '\\' in normalized:
            raise KeyError(f'Skill 名称无效：{skill_name}')
        return normalized

    @classmethod
    def _skill_dir(cls, skill_name: str) -> Path:
        skill_name = cls.normalize_skill_name(skill_name)
        introductions = cls.introductions()
        if skill_name not in introductions:
            raise KeyError(f"Skill 未在 introductions.json 中登记：{skill_name}")
        if not cls._mcp_enabled(introductions[skill_name]):
            raise KeyError(f"Skill 未开放给 MCP：{skill_name}")
        root = cls.skill_root()
        path = (root / skill_name).resolve()
        if path.parent != root or not path.is_dir() or not (path / "SKILL.md").is_file():
            raise FileNotFoundError(f"Skill 目录不存在或缺少 SKILL.md：{skill_name}")
        return path

    @staticmethod
    def _included_file(path: Path, skill_dir: Path) -> bool:
        relative = path.relative_to(skill_dir)
        return (
                path.is_file()
                and not path.is_symlink()
                and not any(part.startswith(".") or part in EXCLUDED_PARTS for part in relative.parts)
                and path.suffix.lower() not in EXCLUDED_SUFFIXES
        )

    @classmethod
    def _skill_files(cls, skill_name: str) -> list[Path]:
        skill_dir = cls._skill_dir(skill_name)
        return sorted(
            (path for path in skill_dir.rglob("*") if cls._included_file(path, skill_dir)),
            key=lambda path: path.relative_to(skill_dir).as_posix(),
        )

    @classmethod
    def _file_record(cls, skill_name: str, path: Path, include_content: bool) -> dict[str, Any]:
        skill_dir = cls._skill_dir(skill_name)
        relative_path = path.relative_to(skill_dir).as_posix()
        content = path.read_bytes()
        record: dict[str, Any] = {
            "path": relative_path,
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        }
        if include_content:
            try:
                record["encoding"] = "utf-8"
                record["content"] = content.decode("utf-8")
            except UnicodeDecodeError:
                record["encoding"] = "base64"
                record["content"] = base64.b64encode(content).decode("ascii")
        return record

    @classmethod
    def skill_manifest(cls, skill_name: str) -> dict[str, Any]:
        skill_name = cls.normalize_skill_name(skill_name)
        introductions = cls.introductions()
        if skill_name not in introductions:
            raise KeyError(f"Skill 未在 introductions.json 中登记：{skill_name}")
        metadata = introductions[skill_name]
        skill_dir = cls._skill_dir(skill_name)
        files = cls._skill_files(skill_name)
        digest = hashlib.sha256()
        introductions_path = cls.skill_root() / "introductions.json"
        digest.update(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\0")
        latest_mtime = introductions_path.stat().st_mtime
        file_records = []
        for path in files:
            record = cls._file_record(skill_name, path, include_content=False)
            relative_path = record["path"]
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
            latest_mtime = max(latest_mtime, path.stat().st_mtime)
            file_records.append(record)
        return {
            "name": skill_name,
            "title": metadata.get("title") or skill_name,
            "category": metadata.get("category"),
            "description": metadata.get("description"),
            "mcp_enabled": True,
            "version": digest.hexdigest(),
            "updated_at": (
                datetime.fromtimestamp(latest_mtime, tz=timezone.utc).isoformat()
                if latest_mtime else None
            ),
            "entrypoint": "SKILL.md",
            "resource_uri": SKILL_RESOURCE_URI_TEMPLATE.format(skill_name=skill_name),
            "file_count": len(file_records),
            "total_size": sum(item["size"] for item in file_records),
            "files": file_records,
        }

    @classmethod
    def catalog(cls, known_versions: dict[str, str] | None = None) -> dict[str, Any]:
        known_versions = known_versions or {}
        items = []
        catalog_digest = hashlib.sha256()
        introductions_bytes = (cls.skill_root() / "introductions.json").read_bytes()
        catalog_digest.update(introductions_bytes)
        for skill_name in cls.mcp_introductions():
            manifest = cls.skill_manifest(skill_name)
            manifest["known_version"] = known_versions.get(skill_name)
            manifest["update_available"] = known_versions.get(skill_name) != manifest["version"]
            items.append(manifest)
            catalog_digest.update(skill_name.encode("utf-8"))
            catalog_digest.update(manifest["version"].encode("ascii"))
        return {
            "catalog_uri": SKILL_CATALOG_URI,
            "catalog_version": catalog_digest.hexdigest(),
            "skill_count": len(items),
            "skills": items,
            "update_workflow": [
                "连接 MCP 后读取本目录，根据 title/category/description 选择与任务匹配的 Skill。",
                "调用 get_mcp_skill 或读取对应 resource_uri，先读 SKILL.md，再按其中路由读取 references。",
                "下次调用 list_mcp_skills 时传入本地 known_versions；update_available=true 时重新获取。",
                "MCP 服务端发布新版本后 URI 不变，version 内容哈希变化，客户端无需重新安装 MCP。",
            ],
        }

    @classmethod
    def get_skill(
            cls,
            skill_name: str,
            *,
            known_version: str | None = None,
            file_path: str | None = None,
            include_files: bool = True,
    ) -> dict[str, Any]:
        skill_name = cls.normalize_skill_name(skill_name)
        manifest = cls.skill_manifest(skill_name)
        if known_version and known_version == manifest["version"] and not file_path:
            return {**manifest, "not_modified": True, "files": []}
        if file_path:
            skill_dir = cls._skill_dir(skill_name)
            target = (skill_dir / file_path).resolve()
            if target == skill_dir or skill_dir not in target.parents or not cls._included_file(target, skill_dir):
                raise FileNotFoundError(f"Skill 文件不存在或不可读取：{file_path}")
            return {
                **manifest,
                "not_modified": False,
                "files": [cls._file_record(skill_name, target, include_content=True)],
            }
        return {
            **manifest,
            "not_modified": False,
            "files": [
                cls._file_record(skill_name, path, include_content=True)
                for path in cls._skill_files(skill_name)
            ] if include_files else manifest["files"],
        }
