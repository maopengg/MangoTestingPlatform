from src.apps.system.schemas.notice import TestReportModel, WeChatNoticeModel, EmailNoticeModel, FeiShuNoticeModel, DingDingNoticeModel
from src.apps.system.services.notice import EmailSend, WeChatSend, FeiShuSend, DingDingSend

from src.apps.system.enums import CacheDataKeyEnum
from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
from mangotools.enums import TaskEnum
from src.apps.system.services.system_config import SystemConfigService
from src.apps.task_center.services.scheduling.task_group_notice import (
    TaskGroupNoticeBuilder,
    TaskGroupNoticeReport,
)
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.exceptions import (
    TEST_NOTICE_EMAIL_CACHE_KEY_EMPTY,
    TestCenterError,
)
from src.apps.test_center.models import NoticeGroup, TestSuite
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService
from src.apps.test_center.services.test_suite.notice_details import ReportNoticeDetailsService
from src.common.decorators.retry import async_task_db_connection


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-11-28 17:58
# @Author : 毛鹏


class NoticeMain:

    def __init__(self, notice_group_id: int):
        """
        初始化通知主类

        Args:
            notice_group_id: 通知组ID
        """
        self.notice_group_id = notice_group_id
        self.notice_obj = NoticeGroup.objects.get(id=notice_group_id)

    @async_task_db_connection(max_retries=3, retry_delay=2)
    def notice_main(self, test_suite_id: int):
        """
        发送测试套件通知

        Args:
            test_suite_id: 测试套件ID
        """
        test_report = self.__test_report(test_suite_id)
        from src.apps.test_center.enums.report_delivery import ReportSourceEnum
        from src.apps.test_center.services.report_delivery import ReportDeliveryService
        session = ReportDeliveryService.prepare(ReportSourceEnum.SUITE, test_suite_id, self.notice_obj)
        if session is not None:
            session.send(self.notice_obj, SystemConfigService.get_platform_name(), self.__get_report_url(test_report),
                         self.__mail_config_dict, suite_report=test_report)
            return
        self.__send_notifications(test_report=test_report)

    @async_task_db_connection(max_retries=3, retry_delay=2)
    def notice_task_group(self, report: TaskGroupNoticeReport):
        """使用任务组专用样式合并发送一个执行批次的全部子报告。"""
        details, note = ReportNoticeDetailsService.collect({child.test_suite_id: child.task_name for child in report.children if child.test_suite_id and child.fail > 0})
        builder = TaskGroupNoticeBuilder(report, self.__get_domain_name(), SystemConfigService.get_platform_name(), details, note)
        if report.execution_id is not None:
            from src.apps.test_center.enums.report_delivery import ReportSourceEnum
            from src.apps.test_center.services.report_delivery import ReportDeliveryService
            session = ReportDeliveryService.prepare(ReportSourceEnum.GROUP, report.execution_id, self.notice_obj)
            if session is not None:
                session.send(self.notice_obj, builder.platform_name, self.__get_domain_name(), self.__mail_config_dict, group_builder=builder)
                return
        if self.notice_obj.mail:
            send_user, email_host, stamp_key = self.__mail_config()
            EmailSend(EmailNoticeModel(
                send_user=send_user,
                email_host=email_host,
                stamp_key=stamp_key,
                send_list=self.notice_obj.mail,
            ), platform_name=builder.platform_name).send_mail(builder.build_title(), builder.build_email_html(), subtype='html')
        if self.notice_obj.work_weixin:
            WeChatSend(
                WeChatNoticeModel(webhook=self.notice_obj.work_weixin)
            ).send_markdown(builder.build_wechat_markdown())
        if self.notice_obj.feishu:
            FeiShuSend(
                FeiShuNoticeModel(webhook=self.notice_obj.feishu)
            ).send_interactive_card(builder.build_feishu_card())
        if self.notice_obj.dingding:
            DingDingSend(
                DingDingNoticeModel(webhook=self.notice_obj.dingding)
            ).send_markdown(builder.build_wechat_markdown())

    @async_task_db_connection(max_retries=3, retry_delay=2)
    def notice_monitoring(self, msg: str):
        """
        发送监控通知

        Args:
            msg: 通知消息内容
        """
        self.__send_notifications(original=True, msg=msg)

    def test_notice_send(self):
        """
        发送测试通知
        """
        test_report = TestReportModel(**{
            "test_suite_id": 197899881973,
            'task_name': None,
            'product_name': '模拟API',
            "project_name": "演示DEMO",
            "test_environment": "生产环境",
            "case_sum": 6,
            "api_case_sum": 1,
            "api_fail": 0,
            "api_call": 1,
            "ui_case_sum": 2,
            "ui_fail": 0,
            "ui_step_call": 7,
            "pytest_case_sum": 3,
            "pytest_fail": 0,
            "pytest_func_call": 3,
            "success": 6,
            "success_rate": 100.0,
            "warning": 0,
            "fail": 0,
            "execution_duration": "03:40:36",
            "test_time": "2025-07-05 06:26:47"
        })
        self.__send_notifications(test_report=test_report)

    def __send_notifications(
            self,
            test_report: TestReportModel | None = None,
            original: bool = False,
            msg: str | None = None
    ):
        if self.notice_obj.mail:
            self.__wend_mail_send(self.notice_obj.mail, test_report, original=original, msg=msg)
        if self.notice_obj.work_weixin:
            self.__we_chat_send(self.notice_obj.work_weixin, test_report, original=original, msg=msg)
        if self.notice_obj.feishu:
            self.__fs_chat_send(self.notice_obj.feishu, test_report, original=original, msg=msg)
        if self.notice_obj.dingding:
            self.__ding_ding_send(self.notice_obj.dingding, test_report, original=original, msg=msg)

    def __we_chat_send(self, webhook, test_report: TestReportModel | None = None, original=False, msg=None):
        try:
            wechat = WeChatSend(WeChatNoticeModel(webhook=webhook), test_report, self.__get_report_url(test_report),
                                platform_name=SystemConfigService.get_platform_name())
            if original:
                wechat.send_text(msg)
            else:
                wechat.send_wechat_notification()
        except TestCenterError:
            raise

    def __fs_chat_send(self, webhook: str, test_report: TestReportModel | None = None, original=False, msg=None):
        try:
            feishu = FeiShuSend(FeiShuNoticeModel(webhook=webhook), test_report, self.__get_report_url(test_report),
                               platform_name=SystemConfigService.get_platform_name())
            if original:
                feishu.send_markdown(msg)
            else:
                feishu.send_feishu_notification()
        except TestCenterError:
            raise

    def __ding_ding_send(self, webhook, test_report: TestReportModel | None = None, original=False, msg=None):
        try:
            dingding = DingDingSend(DingDingNoticeModel(webhook=webhook), test_report, self.__get_report_url(test_report),
                                 platform_name=SystemConfigService.get_platform_name())
            if original:
                dingding.send_text(msg)
            else:
                dingding.send_dingding_notification()
        except TestCenterError:
            raise

    def __wend_mail_send(self, send_list, test_report: TestReportModel | None = None, original=False, msg=None):
        send_user, email_host, stamp_key = self.__mail_config()
        email = EmailSend(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=send_list,
        ), test_report, self.__get_report_url(test_report), platform_name=SystemConfigService.get_platform_name())
        if original:
            email.send_mail(f'预警监控通知', msg)
        else:
            email.send_main()

    @classmethod
    def __test_report(cls, test_suite_id: int) -> TestReportModel:
        test_suite = TestSuite.objects.get(id=test_suite_id)
        execution_duration = test_suite.update_time - test_suite.create_time
        counter = TestSuiteSummaryService.counter_data(test_suite_id)

        case_sum = counter['case_sum']
        success = counter['success']
        fail = counter['fail']
        warning = counter['warning']
        success_rate = 100 if case_sum == 0 else round(success / case_sum * 100, 2)

        # 将秒数转换为HH:MM:SS格式
        total_seconds = int(execution_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        execution_duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        details, note = ReportNoticeDetailsService.collect({test_suite_id: ''}) if fail > 0 else ([], '')
        return TestReportModel(
            failure_details=details,
            failure_details_note=note,
            test_suite_id=test_suite_id,
            case_sum=case_sum,
            excluded_count=counter['excluded_count'],
            success=success,
            success_rate=success_rate,
            warning=warning,
            fail=fail,

            api_case_sum=counter['api_case_sum'],
            api_fail=counter['api_fail'],

            ui_fail=counter['ui_fail'],
            ui_case_sum=counter['ui_case_sum'],

            pytest_fail=counter['pytest_fail'],
            pytest_case_sum=counter['pytest_case_sum'],

            execution_duration=execution_duration_str,
            test_time=test_suite.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            test_environment=EnvironmentEnum.get_value(test_suite.test_env),
            project_name=test_suite.project_product.project.name,
            task_name=test_suite.tasks.name if test_suite.tasks else test_suite.execution_name,
            product_name=test_suite.project_product.name,
        )

    @staticmethod
    def __mail_config():
        try:
            send_user = SystemConfigService.get(CacheDataKeyEnum.SYSTEM_SEND_USER.name)
            email_host = SystemConfigService.get(CacheDataKeyEnum.SYSTEM_EMAIL_HOST.name)
            stamp_key = SystemConfigService.get(CacheDataKeyEnum.SYSTEM_STAMP_KET.name)
        except TestCenterError:
            raise TestCenterError(TEST_NOTICE_EMAIL_CACHE_KEY_EMPTY)
        else:
            if send_user is None or email_host is None or stamp_key is None:
                raise TestCenterError(TEST_NOTICE_EMAIL_CACHE_KEY_EMPTY)
        return send_user, email_host, stamp_key

    @classmethod
    def __mail_config_dict(cls):
        send_user, email_host, stamp_key = cls.__mail_config()
        return {'send_user': send_user, 'email_host': email_host, 'stamp_key': stamp_key}

    @classmethod
    def __get_report_url(cls, test_report: TestReportModel | None = None):
        domain_name = cls.__get_domain_name()
        if not test_report or not test_report.test_suite_id:
            return domain_name
        if not domain_name.startswith(('http://', 'https://')):
            return domain_name
        if TestSuite.objects.filter(id=test_report.test_suite_id,
                report_retention_policy=ReportRetentionPolicyEnum.ABNORMAL_ONLY.value,
                status=TaskEnum.SUCCESS.value).exists():
            return f'{domain_name.rstrip("/")}/#/timing/tasks/index'
        return f'{domain_name.rstrip("/")}/#/report/system/details?id={test_report.test_suite_id}'

    @staticmethod
    def __get_domain_name():
        domain_name = f'请先到系统管理->系统设置中设置：{CacheDataKeyEnum.SYSTEM_DOMAIN_NAME.value}，此处才会显示跳转连接'
        value = SystemConfigService.get(CacheDataKeyEnum.SYSTEM_DOMAIN_NAME.name, default='')
        if value:
            domain_name = value
        return domain_name
