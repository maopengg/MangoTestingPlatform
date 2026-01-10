# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 进程工具类，用于判断是否为主进程
# @Time   : 2026-01-09
# @Author : 毛鹏
import os
import sys
import atexit
from typing import Optional


def is_main_process(lock_name: Optional[str] = None, logger=None) -> bool:
    """
    判断当前进程是否为主进程（实际运行服务器的进程）
    
    用于防止在 Django 自动重载机制下重复执行初始化代码。
    Django 的 runserver 命令会启动两个进程：
    1. 父进程（监控进程）：RUN_MAIN 为 None 或不存在
    2. 子进程（实际运行服务器的进程）：RUN_MAIN='true'
    
    Args:
        lock_name: 可选，锁文件名称（用于需要文件锁的场景，如 auto_system、monitoring）
                   如果提供，将使用文件锁机制确保同一父进程下只有一个进程执行
        logger: 可选，日志记录器，用于记录调试信息
    
    Returns:
        bool: True 表示是重复进程（应该跳过），False 表示是主进程（应该执行）
    
    Examples:
        # 简单模式（只检查 RUN_MAIN 和 DJANGO_SETTINGS_MODULE）
        if is_main_process():
            return  # 跳过重复进程
        
        # 完整模式（包括文件锁）
        if is_main_process(lock_name='mango_system_init', logger=log.system):
            return  # 跳过重复进程
    """
    # 获取当前进程ID
    pid = os.getpid()
    
    # 检查是否为执行 management command 的进程（如 run_monitoring_script）
    # 这些进程不应该执行 apps 的初始化逻辑，因为它们只是临时执行任务
    if len(sys.argv) > 1:
        # 检查是否是 management command（不是 runserver）
        command = sys.argv[1] if len(sys.argv) > 1 else ''
        # 如果是执行 management command（如 run_monitoring_script），跳过初始化
        if command and command != 'runserver' and command != 'runserver_plus' and not command.startswith('--'):
            if logger:
                logger.debug(f"跳过 management command 进程初始化 - PID: {pid}, command: {command}")
            return True
    
    # 检查是否为重载进程
    # RUN_MAIN 是 Django runserver 自动重载器设置的
    # 只有在实际运行服务器的子进程中才会是 'true'
    run_main = os.environ.get('RUN_MAIN', None)
    if run_main != 'true':
        if logger:
            logger.debug(f"跳过重复进程初始化 - PID: {pid}, RUN_MAIN: {run_main}")
        return True
    
    # 检查DJANGO环境变量
    django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
    if not django_settings:
        if logger:
            logger.debug(f"跳过重复进程初始化 - PID: {pid}, DJANGO_SETTINGS_MODULE未设置")
        return True
    
    # 如果提供了锁名称，使用文件锁机制（用于需要更强保护的场景）
    if lock_name:
        # 兼容Windows和Linux系统
        if os.name == 'nt':  # Windows系统
            temp_dir = os.environ.get('TEMP', os.environ.get('TMP', 'C:\\temp'))
            lock_file = f"{temp_dir}\\{lock_name}_{os.getppid()}.lock"
        else:  # Linux/Unix系统
            lock_file = f"/tmp/{lock_name}_{os.getppid()}.lock"
        
        try:
            # 尝试创建锁文件
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL)
            os.close(fd)
            # 注册退出时清理锁文件
            atexit.register(lambda: os.path.exists(lock_file) and os.remove(lock_file))
            if logger:
                logger.debug(f"主进程初始化 - PID: {pid}")
            return False
        except FileExistsError:
            if logger:
                logger.debug(f"跳过重复进程初始化 - PID: {pid}, 锁文件已存在")
            return True
        except Exception as e:
            # 如果无法创建锁文件（如权限问题），使用备用方法
            if logger:
                logger.debug(f"锁文件检查异常 - PID: {pid}, 错误: {e}")
            # 检查父进程ID，避免在子进程中重复执行
            # 使用模块级别的字典来存储已初始化的父进程ID
            if not hasattr(is_main_process, '_initialized_ppids'):
                is_main_process._initialized_ppids = {}
            
            ppid = os.getppid()
            lock_key = f"{lock_name}_{ppid}"
            if lock_key in is_main_process._initialized_ppids:
                return True
            
            is_main_process._initialized_ppids[lock_key] = True
            return False
    
    # 简单模式：只检查 RUN_MAIN 和 DJANGO_SETTINGS_MODULE
    return False
