# -*- coding: utf-8 -*-
from pathlib import PurePosixPath

from src.apps.gray_config.exceptions import (
    GRAY_FILE_REPOSITORY_CONFIG_INVALID,
    GRAY_FILE_REPOSITORY_PATH_CONFIG_INVALID,
    GrayConfigError,
)


class GrayRepositoryPathService:
    @classmethod
    def normalize_dirs(cls, dirs) -> list[str]:
        if dirs in (None, ""):
            return []
        if not isinstance(dirs, list):
            raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_INVALID)
        normalized_dirs = []
        for item in dirs:
            normalized = cls.normalize_repo_path(item, allow_empty=False)
            if normalized and normalized not in normalized_dirs:
                normalized_dirs.append(normalized)
        return normalized_dirs

    @classmethod
    def normalize_file_path(cls, file_path: str) -> str:
        return cls.normalize_repo_path(file_path, allow_empty=False)

    @classmethod
    def ensure_file_allowed(cls, repository, file_path: str) -> str:
        normalized_file_path = cls.normalize_file_path(file_path)
        allowed_dirs = cls.normalize_dirs(getattr(repository, "config_dirs", []) or [])
        if not allowed_dirs:
            return normalized_file_path
        if any(normalized_file_path == item or normalized_file_path.startswith(f"{item}/") for item in allowed_dirs):
            return normalized_file_path
        raise GrayConfigError(GRAY_FILE_REPOSITORY_PATH_CONFIG_INVALID, value=(", ".join(allowed_dirs),))

    @classmethod
    def is_yaml_file_allowed(cls, yaml_file) -> bool:
        if not yaml_file:
            return True
        try:
            repository = getattr(yaml_file, "repository", None)
            file_path = getattr(yaml_file, "file_path", None)
            if repository is None:
                return True
            cls.ensure_file_allowed(repository, file_path)
        except Exception:
            return False
        return True

    @staticmethod
    def normalize_repo_path(value, allow_empty: bool) -> str:
        raw = str(value or "").strip().replace("\\", "/").strip("/")
        if not raw:
            if allow_empty:
                return ""
            raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_INVALID)
        path = PurePosixPath(raw)
        parts = path.parts
        if path.is_absolute() or any(part in ("", ".", "..") for part in parts):
            raise GrayConfigError(GRAY_FILE_REPOSITORY_CONFIG_INVALID)
        return "/".join(parts)
