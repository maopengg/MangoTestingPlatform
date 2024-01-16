# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 企微通知封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import logging

import requests

from PyAutoTest.auto_test.auto_system.models import NoticeConfig, TestObject
from PyAutoTest.exceptions.tools_exception import SendMessageError, ValueTypeError
from PyAutoTest.tools.other_utils.native_ip import get_host_ip

logger = logging.getLogger('system')


class WeChatSend:
    """
    企业微信消息通知
    """

    def __init__(self, notice_obj: NoticeConfig):
        self.config = notice_obj
        self.headers = {"Content-Type": "application/json"}

    def send_wechat_notification(self):
        """
        发送企业微信通知
        :return:
        """
        t = TestObject.objects.filter(project=self.config.project.id).first()
        text = f"""【{self.config.project.name}自动化通知】
                                    >测试环境：<font color=\"info\">{t.name}</font>
                                    >测试负责人：@{t.executor_name.nickname}
                                    >
                                    > **执行结果**
                                    ><font color=\"info\">成  功  率  : {1}%</font>
                                    >执行用例数：<font color=\"info\">{1}</font>                                    
                                    >成功用例数：<font color=\"info\">{1}</font>
                                    >失败用例数：`{1}个`
                                    >异常用例数：`{1}个`
                                    >跳过用例数：<font color=\"warning\">{1}个</font>
                                    >用例执行时长：<font color=\"warning\">{1} s</font>
                                    >测试时间：<font color=\"comment\">{1}</font>
                                    >
                                    >非相关负责人员可忽略此消息。
                                    >测试报告，点击查看>>[测试报告入口](https://{get_host_ip()}:5173)"""

        self.send_markdown(text)

    def send_markdown(self, content):
        """
        发送 MarkDown 类型消息
        :param content: 消息内容，markdown形式
        :return:
        """
        _data = {"msgtype": "markdown", "markdown": {"content": content}}
        res = requests.post(url=self.config.config, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            logger.error(res.json())
            raise SendMessageError("企业微信「MarkDown类型」消息发送失败")

    def send_file_msg(self, file):
        """
        发送文件类型的消息
        @return:
        """

        _data = {"msgtype": "file", "file": {"media_id": self.__upload_file(file)}}
        res = requests.post(url=self.config.config, json=_data, headers=self.headers)
        if res.json()['errcode'] != 0:
            logger.error(res.json())
            raise SendMessageError("企业微信「file类型」消息发送失败")

    def __upload_file(self, file):
        """
        先将文件上传到临时媒体库
        :param file:
        :return:
        """
        data = {"file": open(file, "rb")}
        res = requests.post(url=self.config.config, files=data).json()
        return res['media_id']

    def send_text(self, content, mentioned_mobile_list=None):
        """
        发送文本类型通知
        :param content: 文本内容，最长不超过2048个字节，必须是utf8编码
        :param mentioned_mobile_list: 手机号列表，提醒手机号对应的群成员(@某个成员)，@all表示提醒所有人
        :return:
        """
        _data = {"msgtype": "text", "text": {"content": content, "mentioned_list": None,
                                             "mentioned_mobile_list": mentioned_mobile_list}}

        if mentioned_mobile_list is None or isinstance(mentioned_mobile_list, list):
            # 判断手机号码列表中得数据类型，如果为int类型，发送得消息会乱码
            if len(mentioned_mobile_list) >= 1:
                for i in mentioned_mobile_list:
                    if isinstance(i, str):
                        res = requests.post(url=self.config.config, json=_data, headers=self.headers)
                        if res.json()['errcode'] != 0:
                            logger.error(res.json())
                            raise SendMessageError("企业微信「文本类型」消息发送失败")

                    else:
                        raise ValueTypeError("手机号码必须是字符串类型.")
        else:
            raise ValueTypeError("手机号码列表必须是list类型.")


if __name__ == '__main__':
    # WeChatSend('zshop').send_wechat_notification()
    pass
