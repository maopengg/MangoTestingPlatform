# -*- coding: utf-8 -*-
# @Description: 预警监控脚本运行器
import os
from collections import deque
import re
import subprocess
import threading
import uuid
from typing import Dict, Optional

import sys
import time
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.exceptions import (
    MONITORING_SCRIPT_CONTENT_REQUIRED,
    MONITORING_TASK_EXECUTION_MONITORING_DUPLICATED,
    MonitoringError,
)
from src.apps.monitoring.models import MonitoringTask
from src.apps.system.enums import RuntimeServiceName
from src.common.decorators.system_error import report_system_error, system_error_guard
from src.common.enums.system_error import SystemErrorEventSource


class MonitoringTaskRunner:
    """
    监控任务运行器
    """

    def __init__(self):
        """初始化运行器"""
        self.running_processes: Dict[int, subprocess.Popen] = {}
        self.log_threads: Dict[int, threading.Thread] = {}
        self.preserve_running_on_exit: set[int] = set()

    def active_task_ids(self) -> set[int]:
        active_ids = set()
        for task_id, process in list(self.running_processes.items()):
            if process.poll() is None:
                active_ids.add(task_id)
            else:
                self.running_processes.pop(task_id, None)
                self.log_threads.pop(task_id, None)
        return active_ids

    @staticmethod
    def _is_process_running(pid: int) -> bool:
        """
        检查进程是否正在运行（跨平台）
        """
        if not pid:
            return False
        try:
            # 发送信号 0 不会杀死进程，只是检查进程是否存在
            # Windows 和 Linux 都支持
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            # 进程不存在
            return False
        except Exception:
            # 其他异常（如权限问题），保守地返回 False
            return False

    @staticmethod
    def _kill_process_by_pid(pid: int, timeout: float = 5.0):
        """
        通过 PID 终止进程（跨平台）
        """
        if not pid:
            return
        try:
            if not MonitoringTaskRunner._is_process_running(pid):
                return

            # Windows 系统
            if os.name == 'nt':
                try:
                    # 先尝试优雅终止
                    os.kill(pid, 15)  # Windows 上会转换为 CTRL_BREAK_EVENT
                    time.sleep(timeout)
                    if MonitoringTaskRunner._is_process_running(pid):
                        # 强制终止
                        os.kill(pid, 9)
                except (OSError, ProcessLookupError):
                    # 进程可能已经不存在了
                    pass
                except Exception:
                    # 如果 os.kill 失败，尝试使用 taskkill 命令
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                       capture_output=True, timeout=timeout)
                    except Exception:
                        pass
            else:
                # Linux/Unix 系统
                try:
                    # 先发送 SIGTERM（优雅终止）
                    os.kill(pid, 15)
                    # 等待进程退出
                    for _ in range(int(timeout * 10)):
                        if not MonitoringTaskRunner._is_process_running(pid):
                            return
                        time.sleep(0.1)
                    # 如果还没退出，发送 SIGKILL（强制终止）
                    if MonitoringTaskRunner._is_process_running(pid):
                        os.kill(pid, 9)
                except (OSError, ProcessLookupError):
                    pass
                except Exception:
                    pass
        except Exception:
            pass

    @staticmethod
    def _get_absolute_path(relative_path: str) -> str:
        """
        将相对路径转换为绝对路径。

        监控脚本和日志属于运行时产物，新路径统一写入 runtime/monitoring；
        旧数据中保存的 logs/monitoring、monitoring_scripts 路径继续可读。
        """
        if not relative_path:
            return ''
        if os.path.isabs(relative_path):
            return relative_path
        normalized = relative_path.replace('\\', '/').lstrip('/')
        if normalized.startswith('monitoring/scripts/'):
            return os.path.join(settings.MONITORING_SCRIPT_DIR, normalized[len('monitoring/scripts/'):])
        if normalized.startswith('monitoring/logs/'):
            return os.path.join(settings.MONITORING_LOG_DIR, normalized[len('monitoring/logs/'):])
        if normalized.startswith('monitoring_scripts/'):
            return os.path.join(settings.MONITORING_SCRIPT_DIR, normalized[len('monitoring_scripts/'):])
        if normalized.startswith('logs/monitoring/'):
            return os.path.join(settings.MONITORING_LOG_DIR, normalized[len('logs/monitoring/'):])
        return os.path.join(settings.BASE_DIR, normalized)

    def _append_log(self, log_path: str, text: str):
        """
        追加日志到文件
        log_path 可以是相对路径或绝对路径
        """
        abs_log_path = self._get_absolute_path(log_path)
        os.makedirs(os.path.dirname(abs_log_path), exist_ok=True)
        with open(abs_log_path, 'a', encoding='utf-8') as f:
            f.write(text)
            f.flush()  # 刷新 Python 缓冲区
            os.fsync(f.fileno())  # 强制刷新到磁盘，确保数据立即写入

    def start_task(self, task: MonitoringTask):
        """
        启动监控任务
        """
        # 检查内存中是否已有该任务
        if task.id in self.running_processes:
            proc = self.running_processes[task.id]
            if proc.poll() is None:
                raise MonitoringError(MONITORING_TASK_EXECUTION_MONITORING_DUPLICATED)
            else:
                self.running_processes.pop(task.id, None)

        # 检查数据库中任务状态，如果已经是 RUNNING 且有 PID，先检查进程是否存在
        task.refresh_from_db()
        if task.status not in {
            MonitoringTaskStatusEnum.STARTING.value,
            MonitoringTaskStatusEnum.RUNNING.value,
        }:
            return
        if task.status == MonitoringTaskStatusEnum.RUNNING.value and task.pid:
            if self._is_process_running(task.pid):
                # 进程还在运行，但不在内存中（服务重启导致），先停止旧进程
                from src.common.logging import log
                log.monitoring.info(f'任务 {task.id} ({task.name}) 的进程仍在运行（PID: {task.pid}），先停止旧进程')
                self._kill_process_by_pid(task.pid)
                time.sleep(1)
            # 清空 PID，准备重新启动
            task.pid = None
            task.save(update_fields=['pid'])

        # 从数据库读取代码内容
        if not task.script_content:
            raise MonitoringError(MONITORING_SCRIPT_CONTENT_REQUIRED)

        # 每次启动都生成新的临时文件路径（不保存到数据库）
        file_id = uuid.uuid4().hex
        relative_script_path = os.path.join('monitoring', 'scripts', f'{file_id}.py').replace('\\', '/')
        script_path = self._get_absolute_path(relative_script_path)
        log_path = self._get_absolute_path(task.log_path)

        # 确保目录存在
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self._append_log(
            log_path,
            f'\n[{self._log_timestamp()}] '
            f'[INFO] ===== 开始新的执行：task={task.id} =====\n',
        )

        # 将脚本中的 mangotools 基类导入替换为 Django 项目内的基类导入
        # from mangotools.monitoring import MonitorBase
        #   => from src.apps.monitoring.services.base_monitor import MonitorBase
        script_content = task.script_content
        if script_content:
            script_content = re.sub(
                r'from\s+mangotools\.monitoring\s+import\s+MonitorBase',
                'from src.apps.monitoring.services.base_monitor import MonitorBase',
                script_content,
            )

        # 将代码内容写入文件（不需要添加 Django 初始化代码，因为会通过 management command 执行）
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # 使用 Django management command 来执行脚本，这样脚本自动在 Django 环境中运行
        # 不需要每个脚本都初始化 Django，避免重复导入
        # 使用 -u 参数禁用 Python 的标准输出缓冲，确保日志实时输出
        manage_py_path = os.path.join(settings.BASE_DIR, 'manage.py')
        cmd = [sys.executable, '-u', manage_py_path, 'run_monitoring_script', script_path, str(task.id)]

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

        task.status = MonitoringTaskStatusEnum.RUNNING.value
        task.pid = proc.pid
        task.exit_code = None
        task.started_at = timezone.now()
        task.stopped_at = None
        task.save(update_fields=['status', 'pid', 'exit_code', 'started_at', 'stopped_at'])

        self.running_processes[task.id] = proc
        output_tail = deque(maxlen=100)
        output_lock = threading.Lock()

        @system_error_guard(
            source=SystemErrorEventSource.MONITORING,
            request_path='consume_monitoring_process_output',
            service_name=RuntimeServiceName.MONITORING,
        )
        def _consume_output():
            close_old_connections()
            try:
                if not proc.stdout:
                    return
                for line in proc.stdout:
                    with output_lock:
                        output_tail.append(line[:4096])
                    try:
                        self._append_log(log_path, line)
                    except OSError:
                        # 继续排空子进程输出，避免磁盘异常阻塞脚本，并保留内存错误尾部。
                        pass
            finally:
                close_old_connections()

        @system_error_guard(
            source=SystemErrorEventSource.MONITORING,
            request_path='mark_monitoring_process_finished',
            service_name=RuntimeServiceName.MONITORING,
        )
        def _wait_and_mark():
            close_old_connections()
            try:
                code = proc.wait()
                t_log.join(timeout=5.0)
                task.refresh_from_db()
                if task.id in self.preserve_running_on_exit:
                    next_status = MonitoringTaskStatusEnum.RUNNING.value
                elif task.status == MonitoringTaskStatusEnum.STOPPED.value:
                    next_status = MonitoringTaskStatusEnum.STOPPED.value
                elif code == 0:
                    next_status = MonitoringTaskStatusEnum.COMPLETED.value
                else:
                    next_status = MonitoringTaskStatusEnum.FAILED.value
                task.status = next_status
                task.exit_code = code
                task.pid = None
                task.stopped_at = timezone.now()
                task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at'])
                if next_status == MonitoringTaskStatusEnum.FAILED.value:
                    from src.apps.monitoring.services.task_diagnostic import MonitoringTaskDiagnosticService
                    with output_lock:
                        error_output = ''.join(output_tail)
                    MonitoringTaskDiagnosticService.record(
                        task, f'监控脚本执行失败，退出码：{code}\n' + error_output,
                    )
            finally:
                self.preserve_running_on_exit.discard(task.id)
                self.running_processes.pop(task.id, None)
                self.log_threads.pop(task.id, None)
                close_old_connections()

        t_log = threading.Thread(target=_consume_output, daemon=True)
        t_wait = threading.Thread(target=_wait_and_mark, daemon=True)
        t_log.start()
        t_wait.start()
        self.log_threads[task.id] = t_log

    def stop_task(self, task: MonitoringTask, timeout: float = 5.0, update_status: bool = False):
        """
        停止监控任务
        """
        proc: Optional[subprocess.Popen] = self.running_processes.get(task.id)
        if not proc:
            # 没有运行中的进程，根据update_status参数决定是否更新状态
            if update_status:
                task.status = MonitoringTaskStatusEnum.STOPPED.value
                task.pid = None
                task.stopped_at = timezone.now()
                task.save(update_fields=['status', 'pid', 'stopped_at'])
            else:
                task.pid = None
                task.stopped_at = timezone.now()
                task.save(update_fields=['pid', 'stopped_at'])
            return

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=timeout)

        exit_code = proc.poll()
        self.running_processes.pop(task.id, None)
        self.log_threads.pop(task.id, None)

        # 根据update_status参数决定是否更新状态
        if update_status:
            task.status = MonitoringTaskStatusEnum.STOPPED.value
            task.pid = None
            task.exit_code = exit_code
            task.stopped_at = timezone.now()
            task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at'])
        else:
            # 仅清理PID和退出码信息，保持RUNNING状态以便后续恢复
            task.exit_code = exit_code
            task.pid = None
            task.stopped_at = timezone.now()
            task.save(update_fields=['pid', 'exit_code', 'stopped_at'])

    def stop_task_by_id(self, task_id: int, timeout: float = 5.0) -> bool:
        """停止已无数据库记录的孤儿子进程。"""
        proc = self.running_processes.pop(task_id, None)
        self.log_threads.pop(task_id, None)
        if proc is None:
            return False
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=timeout)
        return True

    def stop_all_tasks(self, timeout: float = 5.0):
        """
        停止所有正在运行的任务（不更改数据库中的任务状态，以便重启时恢复）
        """
        from src.common.logging import log

        log.monitoring.info('开始停止所有监控任务...')

        # 先处理内存中的任务
        running_task_ids = list(self.running_processes.keys())
        log.monitoring.info(f'内存中有 {len(running_task_ids)} 个任务需要停止')

        stopped_count = 0
        for task_id in running_task_ids:
            try:
                proc = self.running_processes.get(task_id)
                if proc and proc.poll() is None:
                    # 进程还在运行，终止它
                    self.preserve_running_on_exit.add(task_id)
                    log.monitoring.info(f'正在终止任务 {task_id} 的进程（PID: {proc.pid}）')
                    proc.terminate()
                    try:
                        proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        log.monitoring.warning(f'任务 {task_id} 进程未在 {timeout} 秒内退出，强制终止')
                        proc.kill()

                # 清理内存引用
                self.running_processes.pop(task_id, None)
                self.log_threads.pop(task_id, None)

                # 重要：不再更新数据库状态，保持RUNNING状态以便重启时恢复
                # 仅清理PID和退出码，保留原始状态
                try:
                    task = MonitoringTask.objects.get(id=task_id)
                    task.pid = None
                    task.exit_code = proc.poll() if proc else None
                    task.stopped_at = timezone.now()
                    task.save(update_fields=['pid', 'exit_code', 'stopped_at'])
                    stopped_count += 1
                    log.monitoring.info(f'任务 {task_id} ({task.name}) 进程已终止，状态保持不变')
                except MonitoringTask.DoesNotExist:
                    # 任务可能已被删除，忽略
                    pass
                except Exception as e:
                    report_system_error(
                        e,
                        source=SystemErrorEventSource.MONITORING,
                        request_path='stop_monitoring_task',
                        service_name=RuntimeServiceName.MONITORING,
                    )
                    log.monitoring.warning(f'更新任务 {task_id} 状态时发生异常: {e}')
            except Exception as e:
                report_system_error(
                    e,
                    source=SystemErrorEventSource.MONITORING,
                    request_path='stop_monitoring_task',
                    service_name=RuntimeServiceName.MONITORING,
                )
                log.monitoring.error(f'停止任务 {task_id} 时发生异常: {e}')
                # 即使失败也清理内存引用
                self.running_processes.pop(task_id, None)
                self.log_threads.pop(task_id, None)

        # 处理数据库中 RUNNING 状态但不在内存中的任务（可能是服务异常退出导致）
        try:
            db_running_tasks = MonitoringTask.objects.filter(status=MonitoringTaskStatusEnum.RUNNING.value)
            db_running_count = db_running_tasks.count()
            if db_running_count > 0:
                log.monitoring.info(f'数据库中有 {db_running_count} 个 RUNNING 状态的任务，将在重启时处理')
                for task in db_running_tasks:
                    try:
                        # 如果进程还在运行，尝试终止它
                        if task.pid and self._is_process_running(task.pid):
                            log.monitoring.info(
                                f'检测到任务 {task.id} ({task.name}) 的进程仍在运行（PID: {task.pid}），正在终止...')
                            self._kill_process_by_pid(task.pid)

                        # 重要：不再更新数据库状态，保持RUNNING状态以便重启时恢复
                        # 仅清理PID，保留原始状态
                        task.pid = None
                        task.save(update_fields=['pid'])
                        stopped_count += 1
                        log.monitoring.info(f'任务 {task.id} ({task.name}) PID已清理，状态保持RUNNING')
                    except Exception as e:
                        report_system_error(
                            e,
                            source=SystemErrorEventSource.MONITORING,
                            request_path='cleanup_monitoring_task_pid',
                            service_name=RuntimeServiceName.MONITORING,
                        )
                        log.monitoring.warning(f'更新任务 {task.id} 状态时发生异常: {e}')
        except Exception as e:
            report_system_error(
                e,
                source=SystemErrorEventSource.MONITORING,
                request_path='stop_all_monitoring_tasks',
                service_name=RuntimeServiceName.MONITORING,
            )
            log.monitoring.error(f'处理数据库中的 RUNNING 任务时发生异常: {e}')

        log.monitoring.info(f'已终止 {stopped_count} 个监控任务的进程，状态保持不变以便重启')

    def restore_running_tasks(self):
        """
        恢复所有RUNNING状态的任务
        """
        from src.common.logging import log
        try:
            log.monitoring.info('开始恢复监控任务状态...')
            # 检查数据库连接是否可用
            from django.db import connection
            if connection.connection is None:
                connection.ensure_connection()

            running_tasks = list(MonitoringTask.objects.filter(status=MonitoringTaskStatusEnum.RUNNING.value))
            log.monitoring.info(f'找到 {len(running_tasks)} 个 RUNNING 状态的任务')

            if not running_tasks:
                log.monitoring.info('没有需要恢复的任务')
                return

            restored_count = 0
            restarted_count = 0

            for task in running_tasks:
                try:
                    task.refresh_from_db()  # 确保获取最新数据

                    # 如果任务有 PID，先检查进程是否存在
                    if task.pid:
                        if self._is_process_running(task.pid):
                            # 进程还在运行，但不在 running_processes 中（服务重启导致）
                            # 先停止旧进程，然后重新启动任务以恢复日志收集
                            log.monitoring.info(
                                f'检测到任务 {task.id} ({task.name}) 的进程仍在运行（PID: {task.pid}），将重新启动以恢复日志收集')
                            self._kill_process_by_pid(task.pid)
                            # 等待一下确保进程已终止
                            time.sleep(1)
                        else:
                            # 进程不存在，清空 PID，准备重新启动
                            log.monitoring.info(
                                f'任务 {task.id} ({task.name}) 的进程不存在（PID: {task.pid}），将重新启动')
                            task.pid = None
                            task.save(update_fields=['pid'])

                    # 无论进程是否存在，都尝试重新启动任务（恢复日志收集）
                    try:
                        log.monitoring.info(f'正在重新启动任务 {task.id} ({task.name})...')
                        self.start_task(task)
                        restarted_count += 1
                        log.monitoring.info(f'任务 {task.id} ({task.name}) 重新启动成功')
                    except Exception as e:
                        log.monitoring.error(f'重新启动任务 {task.id} ({task.name}) 失败: {e}')
                        import traceback
                        traceback.print_exc()
                        # 如果重启失败，不更改任务状态，保持RUNNING以便后续尝试
                        # 仅清理PID，让任务保持RUNNING状态以备后续恢复
                        task.pid = None
                        task.save(update_fields=['pid'])
                        restored_count += 1
                except Exception as e:
                    # 单个任务处理失败不影响其他任务
                    report_system_error(
                        e,
                        source=SystemErrorEventSource.MONITORING,
                        request_path='restore_monitoring_task',
                        service_name=RuntimeServiceName.MONITORING,
                    )
                    log.monitoring.warning(f'恢复任务 {task.id} 状态时发生异常: {e}')
                    import traceback
                    traceback.print_exc()
                    continue

            if restored_count > 0 or restarted_count > 0:
                if restarted_count > 0:
                    log.monitoring.info(
                        f'监控任务状态恢复完成，共恢复 {restored_count} 个任务状态，'
                        f'重新启动 {restarted_count} 个任务以恢复日志收集'
                    )
                else:
                    log.monitoring.info(f'监控任务状态恢复完成，共恢复 {restored_count} 个任务状态')
            else:
                log.monitoring.info('没有需要恢复或重启的任务')
        except (RuntimeError, SystemError) as e:
            # 忽略进程关闭时的错误
            if 'shutdown' in str(e).lower() or 'interpreter' in str(e).lower():
                return
            report_system_error(
                e,
                source=SystemErrorEventSource.MONITORING,
                request_path='restore_monitoring_tasks',
                service_name=RuntimeServiceName.MONITORING,
            )
            from src.common.logging import log
            log.monitoring.error(f'恢复监控任务状态时发生异常: {e}')
        except Exception as e:
            report_system_error(
                e,
                source=SystemErrorEventSource.MONITORING,
                request_path='restore_monitoring_tasks',
                service_name=RuntimeServiceName.MONITORING,
            )
            from src.common.logging import log
            log.monitoring.error(f'恢复监控任务状态时发生异常: {e}')
            import traceback
            traceback.print_exc()

    def tail_log(self, task: MonitoringTask, limit: int = 200):
        """
        读取日志文件内容
        """
        if not task.log_path:
            return []

        # 将相对路径转换为绝对路径
        log_path = self._get_absolute_path(task.log_path)

        if not os.path.exists(log_path):
            return []

        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            if limit <= 0:
                return lines
            return lines[-limit:]
        except Exception:
            return []

    @staticmethod
    def _log_timestamp():
        value = timezone.now()
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime('%Y-%m-%d %H:%M:%S')

    def append_task_log(self, task: MonitoringTask, text: str) -> None:
        if not task.log_path:
            return
        timestamp = self._log_timestamp()
        self._append_log(task.log_path, f'[{timestamp}] [ERROR] {text}\n')
