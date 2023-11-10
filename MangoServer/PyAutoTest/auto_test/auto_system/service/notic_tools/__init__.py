# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.models import NoticeConfig
from PyAutoTest.auto_test.auto_system.service.notic_tools.sendmail import SendEmail
from PyAutoTest.auto_test.auto_system.service.notic_tools.weChatSend import WeChatSend
from PyAutoTest.enums.system_enum import NoticeEnum

log = logging.getLogger('system')


class NoticeMain:
    def __init__(self):
        pass

    @classmethod
    def notice_main(cls):
        log.error('请勿使用此方法')

    @classmethod
    def we_chat_send(cls, i):
        wechat = WeChatSend(i)
        wechat.send_wechat_notification()

    @classmethod
    def wend_mail_send(cls, i):
        email = SendEmail(i)
        email.send_main('测试个数')

    @classmethod
    def test_notice_send(cls, _id):
        notice_obj = NoticeConfig.objects.get(id=_id)
        if notice_obj.type == NoticeEnum.MAIL.value:
            cls.wend_mail_send(notice_obj)
        elif notice_obj.type == NoticeEnum.WECOM.value:
            cls.we_chat_send(notice_obj)
