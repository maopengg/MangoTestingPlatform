# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import json
import logging

from PyAutoTest.auto_test.auto_api.models import ApiCaseResult
from PyAutoTest.auto_test.auto_system.models import NoticeConfig
from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_system.service.notic_tools.sendmail import SendEmail
from PyAutoTest.auto_test.auto_system.service.notic_tools.weChatSend import WeChatSend
from PyAutoTest.auto_test.auto_ui.models import UiCaseResult
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.system_enum import NoticeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions.tools_exception import JsonSerializeError
from PyAutoTest.models.tools_model import TestReportModel, EmailNoticeModel, WeChatNoticeModel

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
            ip='61.183.9.60',
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
    def __we_chat_send(cls, i, test_report: TestReportModel | None = None):

        wechat = WeChatSend(WeChatNoticeModel(webhook=i.config), test_report)
        wechat.send_wechat_notification()

    @classmethod
    def __wend_mail_send(cls, i, test_report: TestReportModel | None = None):
        try:
            config = json.loads(i.config)
        except json.decoder.JSONDecodeError:
            raise JsonSerializeError('邮件的配置详情不是json格式')
        email = SendEmail(EmailNoticeModel(
            send_user=config.get('send_user'),
            email_host=config.get('email_host'),
            stamp_key=config.get('stamp_key'),
            send_list=config.get('send_list'),
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
            ip='61.183.9.60',
            test_environment=test_suite.test_object.name,
            project_name=test_suite.project.name,
            project_id=test_suite.project.id)
