# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import json
import logging

from PyAutoTest.auto_test.auto_api.models import ApiCaseResult
from PyAutoTest.auto_test.auto_system.models import NoticeConfig, CacheData
from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_system.service.notic_tools.mail_send import SendEmail
from PyAutoTest.auto_test.auto_system.service.notic_tools.wechat_send import WeChatSend
from PyAutoTest.auto_test.auto_ui.models import UiCaseResult
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.enums.system_enum import NoticeEnum
from PyAutoTest.enums.tools_enum import StatusEnum, ClientNameEnum
from PyAutoTest.exceptions.tools_exception import JsonSerializeError, CacheKetNullError
from PyAutoTest.models.tools_model import TestReportModel, EmailNoticeModel, WeChatNoticeModel
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0012, ERROR_MSG_0031

log = logging.getLogger('system')


class NoticeMain:

    @classmethod
    def notice_main(cls, project_id: int, test_suite_id: int):
        notice_obj = NoticeConfig.objects.filter(project=project_id, status=StatusEnum.SUCCESS.value)
        for i in notice_obj:
            if i.type == NoticeEnum.MAIL.value:
                cls.__wend_mail_send(i, cls.test_report(test_suite_id))
            elif i.type == NoticeEnum.WECOM.value:
                cls.__we_chat_send(i, cls.test_report(test_suite_id))
            else:
                log.error('暂不支持钉钉打卡')

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
            log.error('暂不支持钉钉打卡')

    @classmethod
    def mail_send(cls, content: str) -> None:
        user_list = ['729164035@qq.com', ]
        send_user, email_host, stamp_key = cls.mail_config()
        email = SendEmail(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=user_list,
        ))
        email.send_mail(user_list, f'【{ClientNameEnum.PLATFORM_CHINESE.value}服务运行通知】', content)

    @classmethod
    def __we_chat_send(cls, i, test_report: TestReportModel | None = None):
        wechat = WeChatSend(WeChatNoticeModel(webhook=i.config), test_report)
        wechat.send_wechat_notification()

    @classmethod
    def __wend_mail_send(cls, i, test_report: TestReportModel | None = None):
        try:
            send_list = json.loads(i.config)
        except json.decoder.JSONDecodeError:
            raise JsonSerializeError(*ERROR_MSG_0012)

        send_user, email_host, stamp_key = cls.mail_config()
        email = SendEmail(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=send_list,
        ), test_report)
        email.send_main()

    @classmethod
    def test_report(cls, test_suite_id: int) -> TestReportModel:
        test_suite = TestSuiteReport.objects.get(id=test_suite_id)
        if test_suite.type == AutoTestTypeEnum.UI.value:
            case_result = UiCaseResult.objects.filter(test_suite_id=test_suite_id)
        else:
            case_result = ApiCaseResult.objects.filter(test_suite_id=test_suite_id).order_by('create_time')
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
            test_environment=test_suite.test_object.name,
            project_name=test_suite.project_product.project.name,
            project_id=test_suite.project_product.project.id)

    @staticmethod
    def mail_config():
        try:
            send_user = CacheData.objects.get(key=CacheDataKeyEnum.SEND_USER.name).value
            email_host = CacheData.objects.get(key=CacheDataKeyEnum.EMAIL_HOST.name).value
            stamp_key = CacheData.objects.get(key=CacheDataKeyEnum.STAMP_KET.name).value
        except CacheData.DoesNotExist:
            raise CacheKetNullError(*ERROR_MSG_0031)
        else:
            if send_user is None or email_host is None or stamp_key is None:
                raise CacheKetNullError(*ERROR_MSG_0031)
        return send_user, email_host, stamp_key
