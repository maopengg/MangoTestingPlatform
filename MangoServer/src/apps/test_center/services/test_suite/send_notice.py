# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2026-01-10 21:57
# @Author : 毛鹏
import threading

from mangotools.enums import StatusEnum

from src.apps.monitoring.enums import MonitoringLogStatusEnum
from src.apps.monitoring.models import MonitoringTask, MonitoringReport
from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.test_center.models import TestSuite
from src.apps.test_center.services.test_suite.base_notice import NoticeMain
from src.common.logging import log


class SendNotice:
    _test_suite_lock = threading.Lock()
    _monitoring_lock = threading.Lock()

    def __init__(self, _id: int):
        self.test_suite = TestSuite.objects.select_related(
            'tasks',
            'tasks__notice_group',
            'tasks__task_group',
            'tasks__task_group__notice_group',
        ).get(id=_id)

    @staticmethod
    def task_notice_config(task):
        """任务组是组内子任务通知配置的唯一来源。"""
        source = task.task_group if task.task_group_id else task
        return source.is_notice, source.fail_notice, source.notice_group_id

    def send_test_suite(self):
        log.system.info(f'开始发送通知：{self.test_suite.id}')
        with self._test_suite_lock:
            from src.apps.test_center.services.test_suite.infrastructure import TestSuiteInfrastructureService
            if TestSuiteInfrastructureService.blocked_suites([self.test_suite.id]).exists():
                return
            # 调度触发的任务组子任务只归集结果，不单独发送通知。
            from src.apps.task_center.services.scheduling.task_group_execution import (
                ScheduledTaskGroupExecutionService,
            )
            if ScheduledTaskGroupExecutionService.complete_test_suite(self.test_suite.id):
                return True
            # 只有测试完成的时候才发送
            if self.test_suite.status not in [StatusEnum.SUCCESS.value, StatusEnum.FAIL.value]:
                return
            # 没有配置定时任务的不发送
            if self.test_suite.tasks is None:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            is_notice, fail_notice, notice_group_id = self.task_notice_config(
                self.test_suite.tasks
            )
            # 任务中没有通知配置的不发送
            if notice_group_id is None:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 任务中有通知配置，没有开启发送的不发送
            if is_notice != StatusEnum.SUCCESS.value:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 任务中开启了失败通知的，就只发送失败通知
            if fail_notice == StatusEnum.SUCCESS.value and self.test_suite.status == StatusEnum.SUCCESS.value:
                self.test_suite.is_notice = TestSuiteNoticeEnum.EXPIRED.value
                self.test_suite.save()
                return
            # 测试套种只=没有发送的才发送
            if not self.test_suite.is_notice == TestSuiteNoticeEnum.NOT_SENT.value:
                return
            updated = TestSuite.objects.filter(
                id=self.test_suite.id,
                is_notice=TestSuiteNoticeEnum.NOT_SENT.value,
            ).update(is_notice=TestSuiteNoticeEnum.SENDING.value)
            if updated == 0:
                return
            self.test_suite.is_notice = TestSuiteNoticeEnum.SENDING.value
            log.system.info(f'成功开始发送通知：{self.test_suite.id}')
            try:
                NoticeMain(notice_group_id).notice_main(self.test_suite.id)
            except Exception:
                self.test_suite.is_notice = TestSuiteNoticeEnum.NOT_SENT.value
                self.test_suite.save(update_fields=['is_notice', 'update_time'])
                raise
            else:
                self.test_suite.is_notice = TestSuiteNoticeEnum.SENT.value
                self.test_suite.save(update_fields=['is_notice', 'update_time'])

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
