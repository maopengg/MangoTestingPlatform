import threading

from src.tools.set_config import SetConfig


class UiCaseConcurrency:
    """两种 UI Case 领取通道共享的本地并发计数。"""

    _lock = threading.RLock()
    _running = 0

    @classmethod
    def capacity(cls) -> int:
        try:
            return max(1, int(SetConfig.get_web_parallel() or 5))  # type: ignore
        except Exception:
            return 5

    @classmethod
    def available(cls) -> int:
        with cls._lock:
            return max(0, cls.capacity() - cls._running)

    @classmethod
    def acquire(cls) -> bool:
        with cls._lock:
            if cls._running >= cls.capacity():
                return False
            cls._running += 1
            return True

    @classmethod
    def reserve(cls, requested: int) -> int:
        """原子预留最多 requested 个槽位，供统一任务领取接口使用。"""
        with cls._lock:
            count = min(max(0, int(requested)), max(0, cls.capacity() - cls._running))
            cls._running += count
            return count

    @classmethod
    def release(cls, count: int = 1) -> None:
        with cls._lock:
            cls._running = max(0, cls._running - max(0, int(count)))

    @classmethod
    def running(cls) -> int:
        with cls._lock:
            return cls._running

    @classmethod
    def reset(cls) -> None:
        """仅供进程重新初始化和测试清理使用。"""
        with cls._lock:
            cls._running = 0
