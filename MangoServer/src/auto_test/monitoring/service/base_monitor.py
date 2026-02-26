# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 监控基类，提供MySQL连接管理和日志输出功能
# @Time   : 2025-01-09
# @Author : 毛鹏
from datetime import datetime

from mangotools.monitoring import MonitorBase as Mb

from src.auto_test.auto_system.service.test_suite.send_notice import SendNotice
from src.auto_test.monitoring.models import MonitoringReport
from src.enums.monitoring_enum import MonitoringLogStatusEnum
from src.tools.decorator.retry import async_task_db_connection


class MonitorBase(Mb):
    """监控基类"""

    @async_task_db_connection
    def run(self):
        pass

    def log(self, message: str, level: str = "INFO"):
        """
        日志输出方法
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
        from django.db import connection
        try:
            connection.close()
            MonitoringReport.objects.create(
                task_id=self.task_id,
                status=status,
                msg=message,
                send_text=log_text,
            )
        except Exception as e:
            self.log(f"监控任务日志失败: {e}")
        finally:
            connection.close()

    def send(self, send_text: str, msg: str = None):
        """
        发送通知
        """
        base_msg = msg if msg else "监控任务失败"
        self.log(f'准备发送消息：{self.task_id}，{base_msg}，{send_text}')

        if not self.task_id:
            return

        SendNotice.send_monitoring(self.task_id, send_text, base_msg)
