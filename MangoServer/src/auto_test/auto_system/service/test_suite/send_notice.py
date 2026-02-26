# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2026-01-10 21:57
# @Author : 毛鹏
import threading

from src.auto_test.auto_system.models import TestSuite
from src.auto_test.auto_system.service.test_suite.base_notice import NoticeMain
from src.auto_test.monitoring.models import MonitoringTask, MonitoringReport
from src.enums.monitoring_enum import MonitoringLogStatusEnum
from src.enums.system_enum import TestSuiteNoticeEnum
from src.enums.tools_enum import StatusEnum
from src.tools.log_collector import log


class SendNotice:
    _test_suite_lock = threading.Lock()
    _monitoring_lock = threading.Lock()

    def __init__(self, _id: int):
        self.test_suite = TestSuite.objects.get(id=_id)

    def send_test_suite(self):
        log.system.info(f'开始发送通知：{self.test_suite.id}')
        with self._test_suite_lock:
            # 只有测试完成的时候才发送
            if self.test_suite.status not in [StatusEnum.SUCCESS.value, StatusEnum.FAIL.value]:
                return
            # 没有配置定时任务的不发送
            if self.test_suite.tasks is None:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 任务中没有通知配置的不发送
            if self.test_suite.tasks.notice_group is None:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 任务中有通知配置，没有开启发送的不发送
            if self.test_suite.tasks.is_notice != StatusEnum.SUCCESS.value:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 任务中开启了失败通知的，就只发送失败通知
            if self.test_suite.tasks.fail_notice == StatusEnum.SUCCESS.value and self.test_suite.status == StatusEnum.SUCCESS.value:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 测试套种只=没有发送的才发送
            if not self.test_suite.is_notice == TestSuiteNoticeEnum.NOT_SENT.value:
                return
            log.system.info(f'成功开始发送通知：{self.test_suite.id}')
            NoticeMain(self.test_suite.tasks.notice_group_id).notice_main(self.test_suite.id)
            self.test_suite.is_notice = StatusEnum.SUCCESS.value
            self.test_suite.save()

    @classmethod
    def send_monitoring(cls, task_id, send_text, base_msg):
        with cls._monitoring_lock:
            task = MonitoringTask.objects.get(id=task_id)
            if task.notice_group is None:
                return
            if task.is_notice != StatusEnum.SUCCESS.value:
                return
            NoticeMain(task.notice_group_id).notice_monitoring(send_text)
            MonitoringReport.objects.create(
                task_id=task_id,
                status=MonitoringLogStatusEnum.ERROR.value,
                msg=base_msg,
                send_text=send_text,
                is_notice=StatusEnum.SUCCESS.value,
            )
