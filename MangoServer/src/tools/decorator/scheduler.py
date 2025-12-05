# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: APScheduler定时任务装饰器
# @Time   : 2025-12-05
# @Author : Qwen

from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler


_scheduler_instance = None


def get_scheduler():
    """获取全局调度器实例"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BackgroundScheduler()
        _scheduler_instance.start()
    return _scheduler_instance


def scheduled_task(trigger_type='interval', **trigger_args):
    """定时任务装饰器
    
    将函数注册为 APScheduler 定时任务
    
    Args:
        trigger_type (str): 触发器类型，支持 'interval', 'cron', 'date'
        **trigger_args: 触发器参数
    
    Examples:
        @scheduled_task('interval', seconds=10)
        def my_task():
            pass
            
        @scheduled_task('cron', hour=2, minute=30)
        def daily_cleanup():
            pass
            
        @scheduled_task('date', run_date='2025-12-05 15:30:00')
        def one_time_task():
            pass
    """
    def decorator(func):
        # 获取调度器实例
        scheduler = get_scheduler()
        
        # 生成任务ID
        job_id = f"{func.__module__}.{func.__name__}"
        
        # 注册任务
        scheduler.add_job(
            func,
            trigger_type,
            id=job_id,
            **trigger_args
        )
        
        # 返回原始函数，不影响正常使用
        return func
    return decorator


def stop_scheduler():
    """停止调度器"""
    global _scheduler_instance
    if _scheduler_instance is not None:
        _scheduler_instance.shutdown()
        _scheduler_instance = None