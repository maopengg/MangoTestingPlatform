# -*- coding: utf-8 -*-
# @Description: 预警监控脚本运行器
import os
import threading
import subprocess
import sys
import uuid
from typing import Dict, Optional

from django.conf import settings
from django.utils import timezone
from django.db import close_old_connections

from src.auto_test.monitoring.models import MonitoringTask

RUNNING_PROCESSES: Dict[int, subprocess.Popen] = {}
LOG_THREADS: Dict[int, threading.Thread] = {}


def _append_log(log_path: str, text: str):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(text)


def start_task(task: MonitoringTask):
    if task.id in RUNNING_PROCESSES:
        proc = RUNNING_PROCESSES[task.id]
        if proc.poll() is None:
            raise RuntimeError('任务已在运行')
        else:
            RUNNING_PROCESSES.pop(task.id, None)

    # 从数据库读取代码内容
    if not task.script_content:
        raise ValueError('任务代码内容为空')

    # 确保目录存在
    scripts_dir = os.path.join(settings.BASE_DIR, 'monitoring_scripts')
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(os.path.dirname(task.log_path), exist_ok=True)

    # 生成文件路径（如果还没有）
    if not task.script_path:
        file_id = uuid.uuid4().hex
        task.script_path = os.path.join(scripts_dir, f'{file_id}.py')
        task.save(update_fields=['script_path'])

    # 将代码内容写入文件
    with open(task.script_path, 'w', encoding='utf-8') as f:
        f.write(task.script_content)

    # 使用当前解释器，确保复用同一虚拟环境/容器的依赖
    cmd = [sys.executable, task.script_path]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        encoding='utf-8',
        errors='ignore',  # 避免因控制台编码(如 gbk)不兼容导致 UnicodeDecodeError
    )

    task.status = MonitoringTask.Status.RUNNING
    task.pid = proc.pid
    task.exit_code = None
    task.started_at = timezone.now()
    task.stopped_at = None
    task.save(update_fields=['status', 'pid', 'exit_code', 'started_at', 'stopped_at', 'updated_at'])

    RUNNING_PROCESSES[task.id] = proc

    def _consume_output():
        close_old_connections()
        try:
            if not proc.stdout:
                return
            for line in proc.stdout:
                _append_log(task.log_path, line)
        finally:
            close_old_connections()

    def _wait_and_mark():
        close_old_connections()
        try:
            code = proc.wait()
            task.refresh_from_db()
            task.exit_code = code
            task.pid = None
            task.stopped_at = timezone.now()
            if task.status == MonitoringTask.Status.RUNNING:
                task.status = MonitoringTask.Status.COMPLETED if code == 0 else MonitoringTask.Status.FAILED
            task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at', 'updated_at'])
        finally:
            RUNNING_PROCESSES.pop(task.id, None)
            LOG_THREADS.pop(task.id, None)
            close_old_connections()

    t_log = threading.Thread(target=_consume_output, daemon=True)
    t_wait = threading.Thread(target=_wait_and_mark, daemon=True)
    t_log.start()
    t_wait.start()
    LOG_THREADS[task.id] = t_log


def stop_task(task: MonitoringTask, timeout: float = 5.0):
    proc: Optional[subprocess.Popen] = RUNNING_PROCESSES.get(task.id)
    if not proc:
        # 没有运行中的进程，直接标记为停止
        task.status = MonitoringTask.Status.STOPPED
        task.pid = None
        task.stopped_at = timezone.now()
        task.save(update_fields=['status', 'pid', 'stopped_at', 'updated_at'])
        return

    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()

    exit_code = proc.poll()
    RUNNING_PROCESSES.pop(task.id, None)
    LOG_THREADS.pop(task.id, None)

    task.status = MonitoringTask.Status.STOPPED
    task.exit_code = exit_code
    task.pid = None
    task.stopped_at = timezone.now()
    task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at', 'updated_at'])


def tail_log(task: MonitoringTask, limit: int = 200):
    if not task.log_path or not os.path.exists(task.log_path):
        return []
    with open(task.log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    if limit <= 0:
        return lines
    return lines[-limit:]

