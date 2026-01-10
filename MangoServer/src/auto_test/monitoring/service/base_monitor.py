# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 监控基类，提供MySQL连接管理和日志输出功能
# @Time   : 2025-01-09
# @Author : 毛鹏
from datetime import datetime

from mangotools.monitoring import MonitorBase as Mb
from src.auto_test.auto_system.service.notice import NoticeMain

from auto_test.auto_system.service.test_suite.send_notice import SendNotice
from src.auto_test.monitoring.models import MonitoringReport
from src.enums.monitoring_enum import MonitoringLogStatusEnum


class MonitorBase(Mb):
    """监控基类，提供MySQL连接管理和日志输出功能"""

    def run(self):
        pass

    def log(self, message: str, level: str = "INFO"):
        """
        日志输出方法，自动添加时间戳，并尝试写入 MonitoringReport 表

        注意：
            - 为了保证此基类可以被抽离到独立库中，所有与 Django 相关的导入
              和写入逻辑都放在函数内部，并使用 try 包裹，失败时仅打印日志。

        Args:
            message: 日志消息
            level: 日志级别 (INFO, ERROR, WARNING, DEBUG)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_text = f"[{timestamp}] [{level}] {message}"
        print(log_text)

        if not self.task_id or level == "INFO":
            return

        level_upper = (level or "INFO").upper()
        level_map = {
            "INFO": MonitoringLogStatusEnum.INFO.value,
            "ERROR": MonitoringLogStatusEnum.ERROR.value,
            "WARNING": MonitoringLogStatusEnum.WARNING.value,
            "DEBUG": MonitoringLogStatusEnum.DEBUG.value,
        }
        status = level_map.get(level_upper, MonitoringLogStatusEnum.INFO.value)

        MonitoringReport.objects.create(
            task_id=self.task_id,
            status=status,
            msg=message,
            send_text=log_text,
        )

    def send(self, send_text: str, msg: str = None):
        """
        写入一条“失败”状态的监控报告日志

        说明：
            - 默认按失败状态写入（ERROR）
            - 需要传入 send_text，msg 为可选说明
            - 为保证此基类可抽离到独立库中，所有 Django 相关导入和写入逻辑
              都放在函数内部并使用 try 包裹，失败时仅打印日志。

        Args:
            send_text: 详细信息（必填，将写入 MonitoringReport.send_text）
            msg: 简要消息（可选，将写入 MonitoringReport.msg）
        """
        base_msg = msg if msg else "监控任务失败"

        if not self.task_id:
            return

        SendNotice.send_monitoring(self.task_id, send_text, base_msg)
