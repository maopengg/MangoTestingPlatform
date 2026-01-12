# -*- coding: utf-8 -*-
# @Description: 预警监控脚本运行器
import os
import re
import threading
import subprocess
import sys
import uuid
import time
from typing import Dict, Optional

from django.conf import settings
from django.utils import timezone
from django.db import close_old_connections

from src.auto_test.monitoring.models import MonitoringTask
from src.enums.monitoring_enum import MonitoringTaskStatusEnum


class MonitoringTaskRunner:
    """
    监控任务运行器
    负责启动、停止、恢复监控任务，以及管理任务进程和日志收集
    """
    
    def __init__(self):
        """初始化运行器"""
        self.running_processes: Dict[int, subprocess.Popen] = {}
        self.log_threads: Dict[int, threading.Thread] = {}
    
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
        将相对路径转换为绝对路径（相对于 BASE_DIR）
        """
        if not relative_path:
            return ''
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(settings.BASE_DIR, relative_path)
    
    def _append_log(self, log_path: str, text: str):
        """
        追加日志到文件
        log_path 可以是相对路径或绝对路径
        """
        abs_log_path = self._get_absolute_path(log_path)
        os.makedirs(os.path.dirname(abs_log_path), exist_ok=True)
        with open(abs_log_path, 'a', encoding='utf-8') as f:
            f.write(text)
            f.flush()  
    
    def start_task(self, task: MonitoringTask):
        """
        启动监控任务
        """
        # 检查内存中是否已有该任务
        if task.id in self.running_processes:
            proc = self.running_processes[task.id]
            if proc.poll() is None:
                raise RuntimeError('任务已在运行')
            else:
                self.running_processes.pop(task.id, None)
        
        # 检查数据库中任务状态，如果已经是 RUNNING 且有 PID，先检查进程是否存在
        task.refresh_from_db()
        if task.status == MonitoringTaskStatusEnum.RUNNING.value and task.pid:
            if self._is_process_running(task.pid):
                # 进程还在运行，但不在内存中（服务重启导致），先停止旧进程
                from src.tools.log_collector import log
                log.system.info(f'任务 {task.id} ({task.name}) 的进程仍在运行（PID: {task.pid}），先停止旧进程')
                self._kill_process_by_pid(task.pid)
                time.sleep(1)
            # 清空 PID，准备重新启动
            task.pid = None
            task.save(update_fields=['pid'])

        # 从数据库读取代码内容
        if not task.script_content:
            raise ValueError('任务代码内容为空')

        # 每次启动都生成新的临时文件路径（不保存到数据库）
        file_id = uuid.uuid4().hex
        relative_script_path = os.path.join('monitoring_scripts', f'{file_id}.py').replace('\\', '/')
        script_path = self._get_absolute_path(relative_script_path)
        log_path = self._get_absolute_path(task.log_path)

        # 确保目录存在
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        # 将脚本中的 mangotools 基类导入替换为 Django 项目内的基类导入
        # from mangotools.monitoring import MonitorBase
        #   => from src.auto_test.monitoring.service.base_monitor import MonitorBase
        script_content = task.script_content
        if script_content:
            script_content = re.sub(
                r'from\s+mangotools\.monitoring\s+import\s+MonitorBase',
                'from src.auto_test.monitoring.service.base_monitor import MonitorBase',
                script_content,
            )

        # 将代码内容写入文件（不需要添加 Django 初始化代码，因为会通过 management command 执行）
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # 使用 Django management command 来执行脚本，这样脚本自动在 Django 环境中运行
        # 不需要每个脚本都初始化 Django，避免重复导入
        manage_py_path = os.path.join(settings.BASE_DIR, 'manage.py')
        cmd = [sys.executable, manage_py_path, 'run_monitoring_script', script_path, str(task.id)]

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

        def _consume_output():
            close_old_connections()
            try:
                if not proc.stdout:
                    return
                for line in proc.stdout:
                    self._append_log(log_path, line)
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
                if task.status == MonitoringTaskStatusEnum.RUNNING.value:
                    task.status = MonitoringTaskStatusEnum.COMPLETED.value if code == 0 else MonitoringTaskStatusEnum.FAILED.value
                task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at'])
            finally:
                self.running_processes.pop(task.id, None)
                self.log_threads.pop(task.id, None)
                close_old_connections()

        t_log = threading.Thread(target=_consume_output, daemon=True)
        t_wait = threading.Thread(target=_wait_and_mark, daemon=True)
        t_log.start()
        t_wait.start()
        self.log_threads[task.id] = t_log
    
    def stop_task(self, task: MonitoringTask, timeout: float = 5.0):
        """
        停止监控任务
        """
        proc: Optional[subprocess.Popen] = self.running_processes.get(task.id)
        if not proc:
            # 没有运行中的进程，直接标记为停止
            task.status = MonitoringTaskStatusEnum.STOPPED.value
            task.pid = None
            task.stopped_at = timezone.now()
            task.save(update_fields=['status', 'pid', 'stopped_at'])
            return

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()

        exit_code = proc.poll()
        self.running_processes.pop(task.id, None)
        self.log_threads.pop(task.id, None)

        task.status = MonitoringTaskStatusEnum.STOPPED.value
        task.exit_code = exit_code
        task.pid = None
        task.stopped_at = timezone.now()
        task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at'])
    
    def stop_all_tasks(self, timeout: float = 5.0):
        """
        停止所有正在运行的任务
        用于服务停止时同步停止所有子进程
        会处理内存中的任务和数据库中 RUNNING 状态的任务
        """
        from src.tools.log_collector import log
        
        log.system.info('开始停止所有监控任务...')
        
        # 先处理内存中的任务
        running_task_ids = list(self.running_processes.keys())
        log.system.info(f'内存中有 {len(running_task_ids)} 个任务需要停止')
        
        stopped_count = 0
        for task_id in running_task_ids:
            try:
                proc = self.running_processes.get(task_id)
                if proc and proc.poll() is None:
                    # 进程还在运行，终止它
                    log.system.info(f'正在终止任务 {task_id} 的进程（PID: {proc.pid}）')
                    proc.terminate()
                    try:
                        proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        log.system.warning(f'任务 {task_id} 进程未在 {timeout} 秒内退出，强制终止')
                        proc.kill()
                
                # 清理内存引用
                self.running_processes.pop(task_id, None)
                self.log_threads.pop(task_id, None)
                
                # 更新数据库状态
                try:
                    task = MonitoringTask.objects.get(id=task_id)
                    task.status = MonitoringTaskStatusEnum.STOPPED.value
                    task.exit_code = proc.poll() if proc else None
                    task.pid = None
                    task.stopped_at = timezone.now()
                    task.save(update_fields=['status', 'pid', 'exit_code', 'stopped_at'])
                    stopped_count += 1
                    log.system.info(f'任务 {task_id} ({task.name}) 已停止')
                except MonitoringTask.DoesNotExist:
                    # 任务可能已被删除，忽略
                    pass
                except Exception as e:
                    log.system.warning(f'更新任务 {task_id} 状态时发生异常: {e}')
            except Exception as e:
                log.system.error(f'停止任务 {task_id} 时发生异常: {e}')
                # 即使失败也清理内存引用
                self.running_processes.pop(task_id, None)
                self.log_threads.pop(task_id, None)
        
        # 处理数据库中 RUNNING 状态但不在内存中的任务（可能是服务异常退出导致）
        try:
            db_running_tasks = MonitoringTask.objects.filter(status=MonitoringTaskStatusEnum.RUNNING.value)
            db_running_count = db_running_tasks.count()
            if db_running_count > 0:
                log.system.info(f'数据库中有 {db_running_count} 个 RUNNING 状态的任务需要更新状态')
                for task in db_running_tasks:
                    try:
                        # 如果进程还在运行，尝试终止它
                        if task.pid and self._is_process_running(task.pid):
                            log.system.info(f'检测到任务 {task.id} ({task.name}) 的进程仍在运行（PID: {task.pid}），正在终止...')
                            self._kill_process_by_pid(task.pid)
                        
                        # 更新数据库状态
                        task.status = MonitoringTaskStatusEnum.STOPPED.value
                        task.pid = None
                        task.stopped_at = timezone.now()
                        task.save(update_fields=['status', 'pid', 'stopped_at'])
                        stopped_count += 1
                        log.system.info(f'任务 {task.id} ({task.name}) 状态已更新为停止')
                    except Exception as e:
                        log.system.warning(f'更新任务 {task.id} 状态时发生异常: {e}')
        except Exception as e:
            log.system.error(f'处理数据库中的 RUNNING 任务时发生异常: {e}')
        
        log.system.info(f'已停止 {stopped_count} 个监控任务')
    
    def restore_running_tasks(self):
        """
        服务启动时恢复任务状态
        检查所有 RUNNING 状态的任务：
        1. 如果进程不存在，更新状态为 STOPPED
        2. 如果进程存在但不在 running_processes 中（服务重启导致），先停止旧进程，然后重新启动任务
        """
        from src.tools.log_collector import log
        try:
            log.system.info('开始恢复监控任务状态...')
            # 检查数据库连接是否可用
            from django.db import connection
            if connection.connection is None:
                connection.ensure_connection()
            
            running_tasks = list(MonitoringTask.objects.filter(status=MonitoringTaskStatusEnum.RUNNING.value))
            log.system.info(f'找到 {len(running_tasks)} 个 RUNNING 状态的任务')
            
            if not running_tasks:
                log.system.info('没有需要恢复的任务')
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
                            log.system.info(f'检测到任务 {task.id} ({task.name}) 的进程仍在运行（PID: {task.pid}），将重新启动以恢复日志收集')
                            self._kill_process_by_pid(task.pid)
                            # 等待一下确保进程已终止
                            time.sleep(1)
                        else:
                            # 进程不存在，清空 PID，准备重新启动
                            log.system.info(f'任务 {task.id} ({task.name}) 的进程不存在（PID: {task.pid}），将重新启动')
                            task.pid = None
                            task.save(update_fields=['pid'])
                    
                    # 无论进程是否存在，都尝试重新启动任务（恢复日志收集）
                    try:
                        log.system.info(f'正在重新启动任务 {task.id} ({task.name})...')
                        self.start_task(task)
                        restarted_count += 1
                        log.system.info(f'任务 {task.id} ({task.name}) 重新启动成功')
                    except Exception as e:
                        log.system.error(f'重新启动任务 {task.id} ({task.name}) 失败: {e}')
                        import traceback
                        traceback.print_exc()
                        # 如果重启失败，标记为停止
                        task.status = MonitoringTaskStatusEnum.STOPPED.value
                        task.pid = None
                        task.stopped_at = timezone.now()
                        task.save(update_fields=['status', 'pid', 'stopped_at'])
                        restored_count += 1
                except Exception as e:
                    # 单个任务处理失败不影响其他任务
                    log.system.warning(f'恢复任务 {task.id} 状态时发生异常: {e}')
                    import traceback
                    traceback.print_exc()
                    continue
            
            if restored_count > 0 or restarted_count > 0:
                if restarted_count > 0:
                    log.system.info(
                        f'监控任务状态恢复完成，共恢复 {restored_count} 个任务状态，'
                        f'重新启动 {restarted_count} 个任务以恢复日志收集'
                    )
                else:
                    log.system.info(f'监控任务状态恢复完成，共恢复 {restored_count} 个任务状态')
            else:
                log.system.info('没有需要恢复或重启的任务')
        except (RuntimeError, SystemError) as e:
            # 忽略进程关闭时的错误
            if 'shutdown' in str(e).lower() or 'interpreter' in str(e).lower():
                return
            from src.tools.log_collector import log
            log.system.error(f'恢复监控任务状态时发生异常: {e}')
        except Exception as e:
            from src.tools.log_collector import log
            log.system.error(f'恢复监控任务状态时发生异常: {e}')
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


# 创建单例实例
_runner_instance = MonitoringTaskRunner()

# 导出函数接口以保持向后兼容
def start_task(task: MonitoringTask):
    """启动监控任务"""
    return _runner_instance.start_task(task)


def stop_task(task: MonitoringTask, timeout: float = 5.0):
    """停止监控任务"""
    return _runner_instance.stop_task(task, timeout)


def stop_all_tasks(timeout: float = 5.0):
    """停止所有正在运行的任务"""
    return _runner_instance.stop_all_tasks(timeout)


def restore_running_tasks():
    """恢复所有正在运行的任务"""
    return _runner_instance.restore_running_tasks()


def tail_log(task: MonitoringTask, limit: int = 200):
    """读取日志文件内容"""
    return _runner_instance.tail_log(task, limit)


# 导出类实例供高级用法
__all__ = [
    'MonitoringTaskRunner',
    'start_task',
    'stop_task',
    'stop_all_tasks',
    'restore_running_tasks',
    'tail_log',
]
