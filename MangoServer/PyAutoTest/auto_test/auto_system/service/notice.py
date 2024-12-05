# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-28 17:58
# @Author : 毛鹏
import json

from PyAutoTest.auto_test.auto_system.models import NoticeConfig, CacheData, TestSuiteDetails, TestSuite, TestObject
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.enums.system_enum import NoticeEnum, CacheDataKeyEnum, EnvironmentEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import *
from PyAutoTest.tools.log_collector import log
from mangokit import EmailSend, WeChatSend, TestReportModel, WeChatNoticeModel, EmailNoticeModel
from mangokit.exceptions.exceptions import ToolsError


class NoticeMain:

    @classmethod
    def notice_main(cls, test_env: int, project_product: int, test_suite_id: int):
        test_object = TestObject.objects.get(environment=test_env, project_product=project_product)
        notice_obj = NoticeConfig.objects.filter(test_object=test_object.id, status=StatusEnum.SUCCESS.value)
        for i in notice_obj:
            if i.type == NoticeEnum.MAIL.value:
                cls.__wend_mail_send(i, cls.test_report(test_suite_id))
            elif i.type == NoticeEnum.WECOM.value:
                cls.__we_chat_send(i, cls.test_report(test_suite_id))
            else:
                log.system.error('暂不支持钉钉打卡')

    @classmethod
    def test_notice_send(cls, _id):
        notice_obj = NoticeConfig.objects.get(id=_id)
        test_report = TestReportModel(
            test_suite_id=123456789,
            case_sum=83,
            success=58,
            success_rate=69.88,
            warning=0,
            fail=0,
            execution_duration=395,
            test_time='2024-01-22 06:35:58',
            test_environment='手动测试环境',
            project_name='手动触发项目',
            project_id=0)
        if notice_obj.type == NoticeEnum.MAIL.value:
            cls.__wend_mail_send(notice_obj, test_report)
        elif notice_obj.type == NoticeEnum.WECOM.value:
            cls.__we_chat_send(notice_obj, test_report)
        else:
            log.system.error('暂不支持钉钉打卡')

    @classmethod
    def __we_chat_send(cls, i, test_report: TestReportModel | None = None):
        try:
            wechat = WeChatSend(WeChatNoticeModel(webhook=i.config), test_report, cls.get_domain_name())
            wechat.send_wechat_notification()
        except ToolsError as error:
            raise MangoServerError(error.code, error.msg)

    @classmethod
    def __wend_mail_send(cls, i, test_report: TestReportModel | None = None):
        try:
            user_info = User.objects.filter(name__in=json.loads(i.config))
        except json.decoder.JSONDecodeError:
            raise SystemEError(*ERROR_MSG_0012)
        else:
            send_list = []
            for i in user_info:
                try:
                    send_list += i.mailbox
                except TypeError:
                    pass
            if not send_list:
                raise SystemEError(*ERROR_MSG_0048)
        send_user, email_host, stamp_key = cls.mail_config()
        email = EmailSend(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=send_list,
        ), test_report, cls.get_domain_name())
        email.send_main()

    @classmethod
    def test_report(cls, test_suite_id: int) -> TestReportModel:
        test_suite = TestSuite.objects.get(id=test_suite_id)
        case_result = TestSuiteDetails.objects.filter(test_suite_id=test_suite_id, type=test_suite.type)
        case_sum = case_result.count()
        success = case_result.filter(status=StatusEnum.SUCCESS.value).count()
        create_time = test_suite.create_time.strftime("%Y-%m-%d %H:%M:%S")
        execution_duration = test_suite.update_time - test_suite.create_time
        success_rate = 100 if success == case_sum else round(success / case_sum * 100, 2)
        return TestReportModel(
            test_suite_id=test_suite_id,
            case_sum=case_sum,
            success=success,
            success_rate=success_rate,
            warning=case_result.filter(status=2).count(),
            fail=case_result.filter(status=StatusEnum.FAIL.value).count(),
            execution_duration=int(execution_duration.total_seconds()),
            test_time=create_time,
            test_environment=EnvironmentEnum.get_value(test_suite.test_env),
            project_name=test_suite.project_product.project.name,
            project_id=test_suite.project_product.project.id)

    @staticmethod
    def mail_config():
        try:
            send_user = CacheData.objects.get(key=CacheDataKeyEnum.SEND_USER.name).value
            email_host = CacheData.objects.get(key=CacheDataKeyEnum.EMAIL_HOST.name).value
            stamp_key = CacheData.objects.get(key=CacheDataKeyEnum.STAMP_KET.name).value
        except CacheData.DoesNotExist:
            raise SystemEError(*ERROR_MSG_0031)
        else:
            if send_user is None or email_host is None or stamp_key is None:
                raise SystemEError(*ERROR_MSG_0031)
        return send_user, email_host, stamp_key

    @classmethod
    def get_domain_name(cls):
        domain_name = f'请先到系统管理->系统设置中设置：{CacheDataKeyEnum.DOMAIN_NAME.value}，此处才会显示跳转连接'
        try:
            cache_data_obj = CacheData.objects.get(key=CacheDataKeyEnum.DOMAIN_NAME.name)
        except CacheData.DoesNotExist:
            pass
        else:
            if cache_data_obj.value:
                domain_name = cache_data_obj.value
        return domain_name
