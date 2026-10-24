# -*- coding: utf-8 -*-
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.settings import settings
from src.tools import project_dir
from src.tools.json_tools import json_dumps
from src.tools.log_collector import log


def save_ui_debug_payload(payload: Any, payload_type: str) -> Path | None:
    """Keep the latest executable UI case or page-step payload for local debugging."""
    if not settings.IS_DEBUG:
        return None

    try:
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode='json')
        target = Path(project_dir.root_path()) / 'tests' / 'test.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(
            prefix='.test.json.',
            suffix='.tmp',
            dir=target.parent,
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as file:
                file.write(json_dumps(payload, indent=2))
                file.write('\n')
            os.replace(temporary_path, target)
        except Exception:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise
        log.debug(f'已保存最近一次UI{payload_type}调试数据：{target}')
        return target
    except Exception as error:
        log.warning(f'保存UI{payload_type}调试数据失败，不影响本次执行：{error}')
        return None
