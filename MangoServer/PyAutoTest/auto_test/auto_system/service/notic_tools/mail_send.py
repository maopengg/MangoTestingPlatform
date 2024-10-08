# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 邮箱通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging
import smtplib
from email.mime.text import MIMEText
from smtplib import SMTPException
from socket import gaierror

from PyAutoTest.auto_test.auto_system.models import CacheData
from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.enums.tools_enum import ClientNameEnum
from PyAutoTest.exceptions.tools_exception import SendMessageError
from PyAutoTest.models.tools_model import TestReportModel, EmailNoticeModel
from PyAutoTest.exceptions.error_msg import ERROR_MSG_0016, ERROR_MSG_0017

log = logging.getLogger('system')


class SendEmail:

    def __init__(self, notice_config: EmailNoticeModel, test_report: TestReportModel = None):
        self.test_report = test_report
        self.notice_config = notice_config

    def send_main(self) -> None:
        domain_name = f'请先到系统管理->系统设置中设置：{CacheDataKeyEnum.DOMAIN_NAME.value}，此处才会显示跳转连接'
        try:
            cache_data_obj = CacheData.objects.get(key=CacheDataKeyEnum.DOMAIN_NAME.name)
        except CacheData.DoesNotExist:
            pass
        else:
            if cache_data_obj.value:
                domain_name = cache_data_obj.value
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
        芒果自动化平台地址：{domain_name}
        详细情况可前往芒果自动化平台查看，非相关负责人员可忽略此消息。谢谢！
        """
        try:
            self.send_mail(self.notice_config.send_list, f'【{ClientNameEnum.PLATFORM_CHINESE.value}通知】', content)
            log.info(f"邮件发送成功:{self.notice_config.model_dump_json()}")
        except SMTPException as error:
            log.error(f"邮件发送失败->错误消息：{error}，错误数据：{self.notice_config.model_dump_json()}")
            raise SendMessageError(*ERROR_MSG_0016)

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
            raise SendMessageError(*ERROR_MSG_0017)

    def error_mail(self, error_message: str) -> None:

        content = f"自动化测试执行完毕，程序中发现异常，请悉知。报错信息如下：\n{error_message}"
        self.send_mail(self.notice_config.send_list, f'{self.test_report.project_name}接口自动化执行异常通知', content)
