"""MCP进程内排空；退出证据仅证明工具已结束，不证明业务请求或资源清理成功。"""
import os
import socket
import threading
from contextlib import contextmanager
from time import monotonic

from django.utils import timezone

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.exceptions import SystemError, SYSTEM_MCP_DRAINING
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.process_identity import RuntimeProcessIdentity


class McpExecutionLifecycle:
    _lock = threading.RLock()
    _pid = None
    _active = 0
    _draining_at = None
    _drained_at = None
    _deadline = None

    @classmethod
    def reset_process(cls):
        if cls._pid != os.getpid():
            cls._pid, cls._active = os.getpid(), 0
            cls._draining_at = cls._drained_at = cls._deadline = None

    @classmethod
    @contextmanager
    def admit(cls):
        with cls._lock:
            cls.reset_process()
            if cls._draining_at is not None:
                raise SystemError(SYSTEM_MCP_DRAINING)
            cls._active += 1
        try:
            yield
        finally:
            with cls._lock:
                cls._active -= 1
                drained = cls._draining_at is not None and cls._active == 0
            if drained:
                cls.record_drained()

    @classmethod
    def begin_drain(cls, seconds=300):
        # 信号处理器只改本地状态，不执行数据库或网络访问。
        with cls._lock:
            cls.reset_process()
            if cls._draining_at is None:
                cls._draining_at = timezone.now().isoformat()
                cls._deadline = monotonic() + seconds

    @classmethod
    def snapshot(cls):
        with cls._lock:
            cls.reset_process()
            return {**RuntimeProcessIdentity.current(), 'active_tools': cls._active,
                    'draining_at': cls._draining_at, 'drained_at': cls._drained_at}

    @classmethod
    def should_exit(cls):
        with cls._lock:
            cls.reset_process()
            return cls._draining_at is not None and (cls._active == 0 or monotonic() >= cls._deadline)

    @classmethod
    def record_drained(cls):
        with cls._lock:
            cls.reset_process()
            if cls._draining_at is None or cls._active != 0:
                return
            cls._drained_at = cls._drained_at or timezone.now().isoformat()
            metadata = cls.snapshot()
        # 使用独立进程身份保留退出证据，避免新Pod心跳覆盖旧执行的凭据。
        try:
            ServiceHeartbeatService.beat(RuntimeServiceName.MCP,
                instance_name='mcp-exit:' + metadata['process_token'], status=0,
                metadata={**metadata, 'worker_name': socket.gethostname()})
        except Exception as error:
            # 留下待核查记录，不能用退出凭据持久化故障覆盖原业务/清理异常。
            from src.common.logging import log
            log.system.error('MCP排空凭据未保存，保留原执行待核查：exception_type=%s', type(error).__name__)
