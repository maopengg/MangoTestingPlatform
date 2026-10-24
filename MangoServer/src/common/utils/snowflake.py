# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-10-26 11:41
# @Author : 毛鹏
import os
import threading

from django.conf import settings
from django.utils.module_loading import import_string


class Snowflake:
    """同一平台数据库内共享持久化号段，不依赖 Pod 或进程编号。"""

    _lock = threading.Lock()
    _next_tick = 0
    _end_tick = 0

    @classmethod
    def _allocate_tick(cls):
        with cls._lock:
            if cls._next_tick >= cls._end_tick:
                allocator = import_string(settings.SNOWFLAKE_BLOCK_ALLOCATOR)
                cls._next_tick, cls._end_tick = allocator()
            tick = cls._next_tick
            cls._next_tick += 1

        return tick

    @classmethod
    def snowflake_id(cls):
        tick = cls._allocate_tick()
        # 保留 41/10/12 位格式；新命名空间与旧版固定的节点 0 隔离。
        return ((tick // 4096) << 22) | (1023 << 12) | (tick % 4096)

    @classmethod
    def _after_fork(cls):
        # fork 不能继承父进程已经领取的号段，也不能继承被占用的线程锁。
        cls._lock = threading.Lock()
        cls._next_tick = cls._end_tick = 0

    @classmethod
    def generate_id(cls):
        # 报告 ID 会作为 JSON 数字传输，使用号段原值以保持在 JS 安全整数范围内。
        return str(cls._allocate_tick())


if hasattr(os, 'register_at_fork'):
    os.register_at_fork(after_in_child=Snowflake._after_fork)
