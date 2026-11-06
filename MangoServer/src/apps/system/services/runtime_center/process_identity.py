import os
import threading
import uuid

from django.utils import timezone


class RuntimeProcessIdentity:
    """同名 Pod/PID 重建后仍不同；fork 后也不继承父进程身份。"""
    _lock = threading.Lock()
    _pid = None
    _identity = None

    @classmethod
    def current(cls):
        with cls._lock:
            if cls._pid != os.getpid():
                cls._pid = os.getpid()
                cls._identity = {'process_token': uuid.uuid4().hex,
                                 'process_started_at': timezone.now().isoformat()}
            return dict(cls._identity)
