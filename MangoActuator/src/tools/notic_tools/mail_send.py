# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 邮箱通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging
import smtplib
from email.mime.text import MIMEText
from socket import gaierror

from src.enums.tools_enum import ClientNameEnum
from src.exceptions.error_msg import ERROR_MSG_0051
from src.exceptions.tools_exception import SendMessageError
from src.models.tools_model import TestReportModel, EmailNoticeModel

log = logging.getLogger('system')


class SendEmail:

    def __init__(self, notice_config: EmailNoticeModel, test_report: TestReportModel = None):
        self.test_report = test_report
        self.notice_config = notice_config

    def send_mail(self, user_list: list, sub: str, content: str, ) -> None:
        try:
            user = f"{ClientNameEnum.PLATFORM_ENGLISH.value} <{self.notice_config.send_user}>"
            message = MIMEText(content, _subtype='plain', _charset='utf-8')  # MIMEText设置发送的内容
            message['Subject'] = sub  # 邮件的主题
            message['From'] = user  # 设置发送人 设置自己的邮箱
            message['To'] = ";".join(user_list)  # 设置收件人 to是收件人，可以是列表
            server = smtplib.SMTP()
            server.connect(self.notice_config.email_host)
            server.login(self.notice_config.send_user, self.notice_config.stamp_key)  # 登录qq邮箱
            server.sendmail(user, user_list, message.as_string())  #
            server.close()
        except gaierror as error:
            log.error(f"邮件发送失败->错误消息：{error}，错误数据：{self.notice_config.model_dump_json()}")
            raise SendMessageError(*ERROR_MSG_0051)

    def error_mail(self, error_message: str) -> None:

        content = f"自动化测试执行完毕，程序中发现异常，请悉知。报错信息如下：\n{error_message}"
        self.send_mail(self.notice_config.send_list, f'{self.test_report.project_name}接口自动化执行异常通知', content)
