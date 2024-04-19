# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 企微通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging

import requests

from PyAutoTest.auto_test.auto_system.models import CacheData
from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.enums.tools_enum import ClientNameEnum
from PyAutoTest.exceptions.tools_exception import SendMessageError, ValueTypeError
from PyAutoTest.models.tools_model import TestReportModel, WeChatNoticeModel
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0013, ERROR_MSG_0014, ERROR_MSG_0018, ERROR_MSG_0019, \
    ERROR_MSG_0020

log = logging.getLogger('system')


class WeChatSend:
    def __init__(self, notice_config: WeChatNoticeModel, test_report: TestReportModel):
        self.notice_config = notice_config
        self.test_report = test_report

        self.headers = {"Content-Type": "application/json"}

    def send_wechat_notification(self):

        domain_name = f'请先到系统管理->系统设置中设置：{CacheDataKeyEnum.DOMAIN_NAME.value}，此处才会显示跳转连接'
        try:
            cache_data_obj = CacheData.objects.get(key=CacheDataKeyEnum.DOMAIN_NAME.name)
        except CacheData.DoesNotExist:
            pass
        else:
            if cache_data_obj.value:
                domain_name = cache_data_obj.value
        text = f"""【{ClientNameEnum.PLATFORM_CHINESE.value}通知】
                    >测试项目：<font color=\"info\">{self.test_report.project_name}</font>
                    >测试环境：{self.test_report.test_environment}
                    >测试套ID：{self.test_report.test_suite_id}
                    >
                    > **执行结果**
                    ><font color=\"info\">成  功  率  : {self.test_report.success_rate}%</font>
                    >执行用例数：<font color=\"info\">{self.test_report.case_sum}</font>                                    
                    >成功用例数：<font color=\"info\">{self.test_report.success}</font>
                    >失败用例数：`{self.test_report.fail}个`
                    >异常用例数：`0 个`
                    >跳过用例数：<font color=\"warning\">0</font>
                    >用例执行时长：<font color=\"warning\">{self.test_report.execution_duration} s</font>
                    >测试时间：<font color=\"comment\">{self.test_report.test_time}</font>
                    >
                    >非相关负责人员可忽略此消息。
                    >测试报告，点击查看>>[测试报告入口]({domain_name})
               """
        self.send_markdown(text)

    def send_markdown(self, content):
        _data = {"msgtype": "markdown", "markdown": {"content": content}}
        res = requests.post(url=self.notice_config.webhook, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            log.error(res.text)
            raise SendMessageError(*ERROR_MSG_0018)

    def send_file_msg(self, file):
        _data = {"msgtype": "file", "file": {"media_id": self.__upload_file(file)}}
        res = requests.post(url=self.notice_config.webhook, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            log.error(res.json())
            raise SendMessageError(*ERROR_MSG_0020)

    def __upload_file(self, file):
        data = {"file": open(file, "rb")}
        res = requests.post(url=self.notice_config.webhook, files=data).json()
        return res['media_id']

    def send_text(self, content, mentioned_mobile_list=None):
        _data = {"msgtype": "text", "text": {"content": content, "mentioned_list": None,
                                             "mentioned_mobile_list": mentioned_mobile_list}}

        if mentioned_mobile_list is None or isinstance(mentioned_mobile_list, list):
            # 判断手机号码列表中得数据类型，如果为int类型，发送得消息会乱码
            if len(mentioned_mobile_list) >= 1:
                for i in mentioned_mobile_list:
                    if isinstance(i, str):
                        res = requests.post(url=self.notice_config.webhook, json=_data, headers=self.headers)
                        if res.json()['errcode'] != 0:
                            log.error(res.json())
                            raise SendMessageError(*ERROR_MSG_0019)

                    else:
                        raise ValueTypeError(*ERROR_MSG_0013)
        else:
            raise ValueTypeError(*ERROR_MSG_0014)


if __name__ == '__main__':
    # WeChatSend('ZASHOP').send_wechat_notification()
    pass
