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
from PyAutoTest.enums.tools_enum import StatusEnum

log = logging.getLogger('system')


class NoticeMain:

    @classmethod
    def notice_main(cls, project_id: int):
        notice_obj = NoticeConfig.objects.filter(project=project_id, status=StatusEnum.SUCCESS.value)
        for i in notice_obj:
            if i.type == NoticeEnum.MAIL.value:
                cls.__wend_mail_send(i)
            elif i.type == NoticeEnum.WECOM.value:
                cls.__we_chat_send(i)
            else:
                log.error('暂不支持钉钉打卡')

    @classmethod
    def test_notice_send(cls, _id):
        notice_obj = NoticeConfig.objects.get(id=_id, status=IsItEnabled.right.value)
        if notice_obj.type == NoticeEnum.MAIL.value:
            cls.__wend_mail_send(notice_obj)
        elif notice_obj.type == NoticeEnum.WECOM.value:
            cls.__we_chat_send(notice_obj)
        else:
            log.error('暂不支持钉钉打卡')

    @classmethod
    def __we_chat_send(cls, i):
        wechat = WeChatSend(i)
        wechat.send_wechat_notification()

    @classmethod
    def __wend_mail_send(cls, i):
        email = SendEmail(i)
        email.send_main('测试个数')
