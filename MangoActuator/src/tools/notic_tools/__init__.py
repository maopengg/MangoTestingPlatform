# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging

from src.enums.tools_enum import ClientNameEnum
from src.models import EmailNoticeModel
from src.tools.notic_tools.mail_send import SendEmail

log = logging.getLogger('system')


class NoticeMain:

    @classmethod
    def mail_send(cls, content: str) -> None:
        user_list = ['729164035@qq.com', ]
        send_user, email_host, stamp_key = '729164035@qq.com', 'smtp.qq.com', 'lqfzvjbpfcwtbecg'
        email = SendEmail(EmailNoticeModel(
            send_user=send_user,
            email_host=email_host,
            stamp_key=stamp_key,
            send_list=user_list,
        ))
        email.send_mail(user_list, f'【{ClientNameEnum.DRIVER.value}服务运行通知】', content)
