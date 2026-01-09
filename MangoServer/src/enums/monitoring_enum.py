# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-08 9:50
# @Author : 毛鹏

from src.enums import BaseEnum


class TaskEnum(BaseEnum):
    """状态枚举"""
    FAIL = 0
    SUCCESS = 1
    STAY_BEGIN = 2
    PROCEED = 3

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "通过", 2: "待开始", 3: "进行中"}


class MonitoringTaskStatusEnum(BaseEnum):
    """监控任务状态枚举"""
    QUEUED = 0
    RUNNING = 1
    STOPPED = 2
    FAILED = 3
    COMPLETED = 4

    @classmethod
    def obj(cls):
        return {
            0: '待执行',
            1: '运行中',
            2: '已停止',
            3: '失败',
            4: '已完成',
        }


class MonitoringLogStatusEnum(BaseEnum):
    """预警监控报告状态枚举"""
    INFO = 0
    ERROR = 1
    WARNING = 2
    DEBUG = 3

    @classmethod
    def obj(cls):
        return {
            0: '信息',
            1: '失败',
            2: '警告',
            3: '调试',
        }
