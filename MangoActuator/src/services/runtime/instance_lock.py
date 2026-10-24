# -*- coding: utf-8 -*-
import os
from pathlib import Path
from typing import IO


class RuntimeInstanceAlreadyRunning(RuntimeError):
    pass


class RuntimeInstanceLock:
    """Keep one actuator process per runtime directory."""

    _process_lock = None

    def __init__(self, lock_path: str):
        self.lock_path = Path(lock_path)
        self._file: IO[str] | None = None

    def acquire(self):
        if self._file is not None:
            return
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.lock_path.open('a+', encoding='utf-8')
        try:
            self._lock_file(lock_file)
        except OSError as error:
            lock_file.seek(0)
            owner_pid = lock_file.read().strip()
            lock_file.close()
            owner_hint = f'（PID {owner_pid}）' if owner_pid.isdigit() else ''
            raise RuntimeInstanceAlreadyRunning(
                f'当前执行器目录已有实例运行{owner_hint}：{self.lock_path.parent.parent}。'
                '如需切换运行模式，请先退出已有实例；如需并行运行，请为 '
                'MANGO_ACTUATOR_RUNTIME_DIR 配置不同目录。'
            ) from error
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        self._file = lock_file

    @classmethod
    def acquire_process_lock(cls, lock_path: str):
        if cls._process_lock is None:
            instance_lock = cls(lock_path)
            instance_lock.acquire()
            cls._process_lock = instance_lock
        return cls._process_lock

    def release(self):
        if self._file is None:
            return
        try:
            self._unlock_file(self._file)
        finally:
            self._file.close()
            self._file = None

    @staticmethod
    def _lock_file(lock_file: IO[str]):
        lock_file.seek(0)
        if os.name == 'nt':
            import msvcrt
            if lock_file.read(1) == '':
                lock_file.write('0')
                lock_file.flush()
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            return
        import fcntl
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _unlock_file(lock_file: IO[str]):
        lock_file.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            return
        import fcntl
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
