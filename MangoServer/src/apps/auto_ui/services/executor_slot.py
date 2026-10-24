import uuid
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock

import sys
import time
from django.core.cache import cache

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_LIVE_EXECUTOR_USER_EXECUTION_REQUIRED,
    UI_LIVE_EXECUTOR_STATUS_EXECUTION_UPDATE_INVALID,
)


class ExecutorSlotLeaseService:
    """OPEN 执行器的跨进程用户容量租约。"""

    MAX_USERS = 5
    IDLE_TIMEOUT_SECONDS = 5 * 60
    STATE_TTL_SECONDS = 24 * 60 * 60
    LOCK_TTL_SECONDS = 5
    _local_lock = RLock()
    _local_states: dict[str, dict] = {}

    @classmethod
    def acquire(
            cls,
            *,
            user: dict,
            connection,
            runtime_type: str,
            resource_id: str | int | None = None,
            workspace_id: str | None = None,
    ) -> dict:
        connection_id = str(connection.connection_id)
        user_id = str(user["id"])
        now = time.time()
        with cls._locked_state(connection_id) as state:
            cls._cleanup_state(state, now)
            slots = state.setdefault("slots", {})
            slot = slots.get(user_id)
            if slot is None:
                if len(slots) >= cls.MAX_USERS:
                    raise AutoUiError(UI_LIVE_EXECUTOR_USER_EXECUTION_REQUIRED,
                                      value=(
                                          connection.user.username,
                                          len(slots),
                                          cls.MAX_USERS,
                                      ),
                                      )
                slot = {
                    "slot_id": str(uuid.uuid4()),
                    "user_id": int(user["id"]),
                    "username": user["username"],
                    "created_at": now,
                    "live_stream_count": 0,
                    "running": False,
                }
                slots[user_id] = slot
            slot.update({
                "runtime_type": str(runtime_type or ""),
                "resource_id": str(resource_id) if resource_id is not None else "",
                "workspace_id": str(workspace_id or slot.get("workspace_id") or ""),
                "last_activity_at": now,
                "idle_deadline": now + cls.IDLE_TIMEOUT_SECONDS,
            })
            cls._refresh_state_metadata(state, connection)
            return cls._slot_payload(slot, len(slots))

    @classmethod
    def touch(
            cls,
            connection_id: str,
            *,
            slot_id: str | None = None,
            user_id: int | None = None,
            runtime_type: str | None = None,
    ) -> dict | None:
        now = time.time()
        with cls._locked_state(str(connection_id)) as state:
            cls._cleanup_state(state, now)
            slot = cls._find_slot(state, slot_id=slot_id, user_id=user_id)
            if slot is None:
                return None
            slot["last_activity_at"] = now
            slot["idle_deadline"] = now + cls.IDLE_TIMEOUT_SECONDS
            if runtime_type:
                slot["runtime_type"] = runtime_type
            return cls._slot_payload(slot, len(state.get("slots") or {}))

    @classmethod
    def set_live(
            cls,
            connection_id: str,
            slot_id: str,
            active: bool,
            stream_id: str | None = None,
    ) -> dict | None:
        now = time.time()
        with cls._locked_state(str(connection_id)) as state:
            cls._cleanup_state(state, now)
            slot = cls._find_slot(state, slot_id=slot_id)
            if slot is None:
                return None
            if stream_id:
                stream_ids = set(slot.get("live_stream_ids") or [])
                if active:
                    stream_ids.add(str(stream_id))
                else:
                    stream_ids.discard(str(stream_id))
                slot["live_stream_ids"] = sorted(stream_ids)
                slot["live_stream_count"] = len(stream_ids)
            else:
                current = int(slot.get("live_stream_count") or 0)
                slot["live_stream_count"] = max(0, current + (1 if active else -1))
            slot["last_activity_at"] = now
            slot["idle_deadline"] = now + cls.IDLE_TIMEOUT_SECONDS
            return cls._slot_payload(slot, len(state.get("slots") or {}))

    @classmethod
    def set_running(
            cls,
            connection_id: str,
            slot_id: str,
            running: bool,
            execution_id: str | None = None,
    ) -> dict | None:
        now = time.time()
        with cls._locked_state(str(connection_id)) as state:
            cls._cleanup_state(state, now)
            slot = cls._find_slot(state, slot_id=slot_id)
            if slot is None:
                return None
            if execution_id:
                running_ids = set(slot.get("running_execution_ids") or [])
                if running:
                    running_ids.add(str(execution_id))
                else:
                    running_ids.discard(str(execution_id))
                slot["running_execution_ids"] = sorted(running_ids)
                slot["running"] = bool(running_ids)
            else:
                slot["running"] = bool(running)
            slot["last_activity_at"] = now
            slot["idle_deadline"] = now + cls.IDLE_TIMEOUT_SECONDS
            return cls._slot_payload(slot, len(state.get("slots") or {}))

    @classmethod
    def release(
            cls,
            connection_id: str,
            *,
            slot_id: str | None = None,
            user_id: int | None = None,
    ) -> bool:
        with cls._locked_state(str(connection_id)) as state:
            slot = cls._find_slot(state, slot_id=slot_id, user_id=user_id)
            if slot is None:
                return False
            state.setdefault("slots", {}).pop(str(slot["user_id"]), None)
            return True

    @classmethod
    def occupancy(cls, connection) -> dict:
        connection_id = str(connection.connection_id)
        now = time.time()
        with cls._locked_state(connection_id) as state:
            cls._cleanup_state(state, now)
            cls._refresh_state_metadata(state, connection)
            slots = list((state.get("slots") or {}).values())
            return {
                "active_user_count": len(slots),
                "max_user_count": cls.MAX_USERS,
                "available_user_count": max(0, cls.MAX_USERS - len(slots)),
                "is_full": len(slots) >= cls.MAX_USERS,
                "users": [
                    {
                        "user_id": item["user_id"],
                        "username": item["username"],
                        "runtime_type": item.get("runtime_type") or "",
                        "idle_deadline": item.get("idle_deadline"),
                    }
                    for item in slots
                ],
            }

    @classmethod
    def clear_connection(cls, connection_id: str) -> None:
        if cls._use_local_store():
            with cls._local_lock:
                cls._local_states.pop(str(connection_id), None)
            return
        cache.delete(cls._state_key(str(connection_id)))

    @classmethod
    def reset_for_tests(cls) -> None:
        with cls._local_lock:
            cls._local_states.clear()

    @classmethod
    @contextmanager
    def _locked_state(cls, connection_id: str):
        if cls._use_local_store():
            with cls._local_lock:
                state = deepcopy(cls._local_states.get(connection_id) or {
                    "connection_id": connection_id,
                    "slots": {},
                })
                yield state
                cls._local_states[connection_id] = deepcopy(state)
            return
        lock_key = cls._lock_key(connection_id)
        lock_token = uuid.uuid4().hex
        acquired = False
        for _ in range(50):
            if cache.add(lock_key, lock_token, timeout=cls.LOCK_TTL_SECONDS):
                acquired = True
                break
            time.sleep(0.01)
        if not acquired:
            raise AutoUiError(UI_LIVE_EXECUTOR_STATUS_EXECUTION_UPDATE_INVALID)
        try:
            state = cache.get(cls._state_key(connection_id)) or {
                "connection_id": connection_id,
                "slots": {},
            }
            yield state
            cache.set(
                cls._state_key(connection_id),
                state,
                timeout=cls.STATE_TTL_SECONDS,
            )
        finally:
            if cache.get(lock_key) == lock_token:
                cache.delete(lock_key)

    @classmethod
    def _cleanup_state(cls, state: dict, now: float) -> None:
        slots = state.setdefault("slots", {})
        expired_user_ids = [
            user_id
            for user_id, slot in slots.items()
            if not slot.get("running")
               and int(slot.get("live_stream_count") or 0) <= 0
               and float(slot.get("idle_deadline") or 0) <= now
        ]
        for user_id in expired_user_ids:
            slots.pop(user_id, None)

    @staticmethod
    def _find_slot(
            state: dict,
            *,
            slot_id: str | None = None,
            user_id: int | None = None,
    ) -> dict | None:
        slots = state.get("slots") or {}
        if user_id is not None:
            return slots.get(str(user_id))
        if slot_id:
            return next(
                (item for item in slots.values() if item.get("slot_id") == str(slot_id)),
                None,
            )
        return None

    @classmethod
    def _slot_payload(cls, slot: dict, active_user_count: int) -> dict:
        return {
            **deepcopy(slot),
            "active_user_count": active_user_count,
            "max_user_count": cls.MAX_USERS,
            "available_user_count": max(0, cls.MAX_USERS - active_user_count),
            "is_full": active_user_count >= cls.MAX_USERS,
            "idle_timeout_seconds": cls.IDLE_TIMEOUT_SECONDS,
        }

    @staticmethod
    def _refresh_state_metadata(state: dict, connection) -> None:
        state["connection_id"] = str(connection.connection_id)
        state["executor_username"] = getattr(
            getattr(connection, "user", None),
            "username",
            state.get("executor_username") or "",
        )
        state["updated_at"] = time.time()

    @staticmethod
    def _state_key(connection_id: str) -> str:
        return f"ui-executor-slots:{connection_id}"

    @staticmethod
    def _lock_key(connection_id: str) -> str:
        return f"ui-executor-slots-lock:{connection_id}"

    @staticmethod
    def _use_local_store() -> bool:
        return "test" in sys.argv
