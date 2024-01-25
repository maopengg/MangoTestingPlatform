# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 邮箱通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging
import smtplib
from email.mime.text import MIMEText
from smtplib import SMTPException
from socket import gaierror

from PyAutoTest.enums.tools_enum import ClientNameEnum
from PyAutoTest.exceptions.tools_exception import SendMessageError
from PyAutoTest.models.tools_model import TestReportModel, EmailNoticeModel

logger = logging.getLogger('system')


class SendEmail:
    """ 发送邮箱 """

    def __init__(self, notice_config: EmailNoticeModel, test_report: TestReportModel):
        self.test_report = test_report
        self.notice_config = notice_config

    def send_main(self) -> None:
        """
        发送邮件
        :return:
        """
        content = f"""
        各位同事, 大家好:
            测试套ID：{self.test_report.test_suite_id}任务执行完成，执行结果如下:
            用例运行总数: {self.test_report.case_sum} 个
            通过用例个数: {self.test_report.success} 个
            失败用例个数: {self.test_report.fail} 个
            异常用例个数: {self.test_report.warning} 个
            跳过用例个数: 暂不统计 个
            成  功   率: {self.test_report.success_rate} %


        **********************************
        芒果自动化平台地址：https://{self.test_report.ip}:8002/#/login
        详细情况可前往芒果自动化平台查看，非相关负责人员可忽略此消息。谢谢！
        """
        try:
            self.send_mail(self.notice_config.send_list, f'【{ClientNameEnum.PLATFORM_CHINESE.value}通知】', content)
            logger.info(f"邮件发送成功:{self.notice_config.json()}")
        except SMTPException as error:
            logger.error(f"邮件发送失败->错误消息：{error}，错误数据：{self.notice_config.json()}")
            raise SendMessageError("邮件发送失败，请检查邮件配置是否正确")

    def send_mail(self, user_list: list, sub: str, content: str, ) -> None:
        """

        @param user_list: 发件人邮箱
        @param sub:
        @param content: 发送内容
        @return:
        """
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
            logger.error(f"邮件发送失败->错误消息：{error}，错误数据：{self.notice_config.json()}")
            raise SendMessageError("请检查email_host是否正确，导致无法连接发送错误")

    def error_mail(self, error_message: str) -> None:
        """
        执行异常邮件通知
        @param error_message: 报错信息
        @return:
        """
        content = f"自动化测试执行完毕，程序中发现异常，请悉知。报错信息如下：\n{error_message}"
        self.send_mail(self.notice_config.send_list, f'{self.test_report.project_name}接口自动化执行异常通知', content)
