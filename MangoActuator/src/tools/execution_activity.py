from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from datetime import datetime
from typing import Any

from src.enums.tools_enum import MessageEnum
from src.tools.send_global_msg import send_global_msg


def execution_identity(model: Any, prefix: str = "task") -> str:
    for field in ("execution_id", "workspace_id", "slot_id", "check_id", "id"):
        value = getattr(model, field, None)
        if value not in (None, ""):
            return f"{prefix}:{value}"
    return f"{prefix}:{id(model)}"


class ExecutionActivity:
    """执行器首页使用的进程内任务快照。"""

    _lock = threading.RLock()
    _active: OrderedDict[str, dict] = OrderedDict()
    _recent: deque[dict] = deque(maxlen=8)

    @classmethod
    def start(cls, task_id: str, task_type: str, task_name: str, operator: str = "",
              progress_total: int = 0) -> str:
        now = time.time()
        with cls._lock:
            cls._active[task_id] = {
                "task_id": task_id,
                "task_type": task_type,
                "task_name": task_name or "未命名任务",
                "operator": operator or "-",
                "status": "running",
                "current_action": "正在初始化",
                "progress_current": 0,
                "progress_total": max(0, int(progress_total)),
                "started_at": now,
                "updated_at": now,
                "finished_at": None,
                "error_message": "",
            }
            cls._active.move_to_end(task_id, last=False)
            cls._emit_locked()
        return task_id

    @classmethod
    def update(cls, task_id: str, current_action: str | None = None,
               progress_current: int | None = None, progress_total: int | None = None) -> None:
        with cls._lock:
            task = cls._active.get(task_id)
            if not task:
                return
            if current_action is not None:
                task["current_action"] = current_action
            if progress_current is not None:
                task["progress_current"] = max(0, int(progress_current))
            if progress_total is not None:
                task["progress_total"] = max(0, int(progress_total))
            task["updated_at"] = time.time()
            cls._active.move_to_end(task_id, last=False)
            cls._emit_locked()

    @classmethod
    def finish(cls, task_id: str, success: bool, error_message: str = "") -> None:
        with cls._lock:
            task = cls._active.pop(task_id, None)
            if not task:
                return
            now = time.time()
            task.update({
                "status": "success" if success else "failed",
                "current_action": "执行完成" if success else "执行失败",
                "updated_at": now,
                "finished_at": now,
                "error_message": str(error_message or ""),
            })
            cls._recent.appendleft(task)
            cls._emit_locked()

    @classmethod
    def snapshot(cls) -> dict:
        with cls._lock:
            return cls._snapshot_locked()

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._active.clear()
            cls._recent.clear()

    @classmethod
    def _snapshot_locked(cls) -> dict:
        def serialize(item: dict) -> dict:
            result = dict(item)
            for field in ("started_at", "updated_at", "finished_at"):
                value = result.get(field)
                result[f"{field}_text"] = (
                    datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S") if value else "-"
                )
            result["elapsed_seconds"] = max(0, int((result.get("finished_at") or time.time()) - result["started_at"]))
            return result

        return {
            "active": [serialize(item) for item in cls._active.values()],
            "recent": [serialize(item) for item in cls._recent],
        }

    @classmethod
    def _emit_locked(cls) -> None:
        send_global_msg(cls._snapshot_locked(), MessageEnum.EXECUTION_STATE)
