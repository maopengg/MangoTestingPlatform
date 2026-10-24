from contextlib import contextmanager
from uuid import uuid4

# -*- coding: utf-8 -*-
import time
from django.core.cache import cache

from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_REPOSITORY_LOCKED,
)
from src.common.logging import log


class GitRepositoryLockService:
    _lock_key = "pytest_git_repository_lock"
    _ttl_seconds = 600
    _wait_seconds = 3
    _sleep_seconds = 0.2

    @classmethod
    @contextmanager
    def locked(cls, operation: str, repository_id: int):
        token = f"{operation}:{uuid4()}"
        lock_key = f"{cls._lock_key}:{repository_id}"
        deadline = time.monotonic() + cls._wait_seconds
        acquired = False
        while time.monotonic() < deadline:
            if cache.add(lock_key, token, timeout=cls._ttl_seconds):
                acquired = True
                break
            time.sleep(cls._sleep_seconds)

        if not acquired:
            raise AutoPytestError(PYTEST_REPOSITORY_LOCKED)

        try:
            yield
        finally:
            try:
                if cache.get(lock_key) == token:
                    cache.delete(lock_key)
            except Exception as error:
                log.pytest.warning(f"释放 Pytest Git 仓库锁失败：{error}")
