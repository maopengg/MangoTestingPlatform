# -*- coding: utf-8 -*-
import os
from pathlib import Path

from django.conf import settings

GRAY_WORKSPACE_NAME = "gray"


class GitWorkspacePathService:
    @staticmethod
    def gray_warehouse_name(repository_id: int) -> str:
        warehouse_name = os.path.join(GRAY_WORKSPACE_NAME, f"mango_gray_{repository_id}")
        GitWorkspacePathService.ensure_workspace_parent(warehouse_name)
        return warehouse_name

    @staticmethod
    def ensure_workspace_parent(warehouse_name: str) -> str:
        path = os.path.dirname(os.path.join(settings.GIT_WORKSPACE_DIR, warehouse_name))
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def ensure_path(path: str) -> str:
        parent = path if os.path.splitext(path)[1] == "" else os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return path

    @staticmethod
    def safe_dir_name(value: str | None) -> str:
        raw = str(value or "").strip().strip("/\\")
        if not raw:
            return ""
        name = Path(raw).name
        return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in name)
