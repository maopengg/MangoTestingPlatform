# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-28 17:58
# @Author : 毛鹏

from django.utils.timezone import localtime
from mangotools.models import TestReportModel, WeChatNoticeModel, EmailNoticeModel, FeiShuNoticeModel
from mangotools.notice import EmailSend, WeChatSend, FeiShuSend

from src.auto_test.auto_system.models import NoticeGroup, CacheData, TestSuite, TestSuiteDetails
from src.enums.system_enum import CacheDataKeyEnum
from src.enums.tools_enum import EnvironmentEnum, TestCaseTypeEnum
from src.exceptions import *
from src.tools.decorator.retry import async_task_db_connection


class NoticeMain:

    def __init__(self, notice_group_id: int):
        """
        初始化通知主类
        
        Args:
            notice_group_id: 通知组ID
        """
        self.notice_group_id = notice_group_id
        self.notice_obj = NoticeGroup.objects.get(id=notice_group_id)

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=2)
    def notice_main(cls, notice_group_id: int, test_suite_id: int):
        """
        发送测试套件通知
        
        Args:
            notice_group_id: 通知组ID
            test_suite_id: 测试套件ID
        """
        notice_obj = cls.__get_notice_group(notice_group_id)
        test_report = cls.__test_report(test_suite_id)
        cls.__send_notifications(notice_obj, test_report=test_report)

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=2)
    def notice_monitoring(cls, notice_group_id: int, msg: str):
        """
        发送监控通知
        
        Args:
            notice_group_id: 通知组ID
            msg: 通知消息内容
        """
        notice_obj = cls.__get_notice_group(notice_group_id)
        cls.__send_notifications(notice_obj, original=True, msg=msg)

    @classmethod
    def test_notice_send(cls, _id: int):
        """
        发送测试通知（用于测试）
        
        Args:
            _id: 通知组ID
        """
        notice_obj = cls.__get_notice_group(_id)
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
        cls.__send_notifications(notice_obj, test_report=test_report)

    @classmethod
    def __get_notice_group(cls, notice_group_id: int) -> NoticeGroup:
        """
        获取通知组对象（提取的公共方法）
        
        Args:
            notice_group_id: 通知组ID
            
        Returns:
            NoticeGroup: 通知组对象
        """
        return NoticeGroup.objects.get(id=notice_group_id)

    @classmethod
    def __send_notifications(
        cls,
        notice_obj: NoticeGroup,
        test_report: TestReportModel | None = None,
        original: bool = False,
        msg: str | None = None
    ):
        """
        发送所有类型的通知（提取的公共方法）
        
        Args:
            notice_obj: 通知组对象
            test_report: 测试报告对象（可选）
            original: 是否发送原始消息
            msg: 原始消息内容（当 original=True 时使用）
        """
        if notice_obj.mail:
            cls.__wend_mail_send(notice_obj.mail, test_report, original=original, msg=msg)
        if notice_obj.work_weixin:
            cls.__we_chat_send(notice_obj.work_weixin, test_report, original=original, msg=msg)
        if notice_obj.feishu:
            cls.__fs_chat_send(notice_obj.feishu, test_report, original=original, msg=msg)
        if notice_obj.dingding:
            cls.__ding_ding_send(notice_obj.dingding, test_report, original=original, msg=msg)

    @classmethod
    def __we_chat_send(cls, webhook, test_report: TestReportModel | None = None, original=False, msg=None):
        """发送企业微信通知（私有方法）"""
        try:
            wechat = WeChatSend(WeChatNoticeModel(webhook=webhook), test_report, cls.__get_domain_name())
            if original:
                wechat.send_text(msg)
            else:
                wechat.send_wechat_notification()
        except ToolsError as error:
            raise MangoServerError(error.code, error.msg)

    @classmethod
    def __fs_chat_send(cls, webhook: str, test_report: TestReportModel | None = None, original=False, msg=None):
        """发送飞书通知（私有方法）"""
        try:
            feishu = FeiShuSend(FeiShuNoticeModel(webhook=webhook), test_report, cls.__get_domain_name())
            if original:
                feishu.send_markdown(msg)
            else:
                feishu.send_feishu_notification()
        except ToolsError as error:
            raise MangoServerError(error.code, error.msg)

    @classmethod
    def __ding_ding_send(cls, webhook, test_report: TestReportModel | None = None, original=False, msg=None):
        """发送钉钉通知（私有方法）"""
        try:
            dingding = FeiShuSend(FeiShuNoticeModel(webhook=webhook), test_report, cls.__get_domain_name())
            if original:
                dingding.send_text(msg)
            else:
                dingding.send_feishu_notification()
        except ToolsError as error:
            raise MangoServerError(error.code, error.msg)

    @classmethod
    def __wend_mail_send(cls, send_list, test_report: TestReportModel | None = None, original=False, msg=None):
        """发送邮件通知（私有方法）"""
        send_user, email_host, stamp_key = cls.__mail_config()
        email = EmailSend(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=send_list,
        ), test_report, cls.__get_domain_name())
        if original:
            email.send_mail(f'预警监控通知', msg)
        else:
            email.send_main()

    @classmethod
    def __test_report(cls, test_suite_id: int) -> TestReportModel:
        test_suite = TestSuite.objects.get(id=test_suite_id)
        execution_duration = test_suite.update_time - test_suite.create_time
        case_sum = 0
        success = 0
        fail = 0
        warning = 0

        api_case_sum = 0
        api_fail = 0

        ui_fail = 0
        ui_case_sum = 0

        pytest_fail = 0
        pytest_case_sum = 0
        model = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id)
        for i in model:
            case_sum += i.case_sum
            success += i.success
            fail += i.fail
            warning += i.warning
            if i.type == TestCaseTypeEnum.API.value:
                api_case_sum += i.case_sum
                api_fail += i.fail
            elif i.type == TestCaseTypeEnum.UI.value:
                ui_case_sum += i.case_sum
                ui_fail += i.fail
            else:
                pytest_case_sum += i.case_sum
                pytest_fail += i.fail

        success_rate = 100 if case_sum == 0 else round(success / case_sum * 100, 2)

        # 将秒数转换为HH:MM:SS格式
        total_seconds = int(execution_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        execution_duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return TestReportModel(
            test_suite_id=test_suite_id,
            case_sum=case_sum,
            success=success,
            success_rate=success_rate,
            warning=warning,
            fail=fail,

            api_case_sum=api_case_sum,
            api_fail=api_fail,

            ui_fail=ui_fail,
            ui_case_sum=ui_case_sum,

            pytest_fail=pytest_fail,
            pytest_case_sum=pytest_case_sum,

            execution_duration=execution_duration_str,
            test_time=localtime(test_suite.create_time).strftime("%Y-%m-%d %H:%M:%S"),
            test_environment=EnvironmentEnum.get_value(test_suite.test_env),
            project_name=test_suite.project_product.project.name,
            task_name=test_suite.tasks.name if test_suite.tasks else None,
            product_name=test_suite.project_product.name,
        )

    @staticmethod
    def __mail_config():
        try:
            send_user = CacheData.objects.get(key=CacheDataKeyEnum.SYSTEM_SEND_USER.name).value
            email_host = CacheData.objects.get(key=CacheDataKeyEnum.SYSTEM_EMAIL_HOST.name).value
            stamp_key = CacheData.objects.get(key=CacheDataKeyEnum.SYSTEM_STAMP_KET.name).value
        except CacheData.DoesNotExist:
            raise SystemEError(*ERROR_MSG_0031)
        else:
            if send_user is None or email_host is None or stamp_key is None:
                raise SystemEError(*ERROR_MSG_0031)
        return send_user, email_host, stamp_key

    @classmethod
    def __get_domain_name(cls):
        domain_name = f'请先到系统管理->系统设置中设置：{CacheDataKeyEnum.SYSTEM_DOMAIN_NAME.value}，此处才会显示跳转连接'
        try:
            cache_data_obj = CacheData.objects.get(key=CacheDataKeyEnum.SYSTEM_DOMAIN_NAME.name)
        except CacheData.DoesNotExist:
            pass
        else:
            if cache_data_obj.value:
                domain_name = cache_data_obj.value
        return domain_name
