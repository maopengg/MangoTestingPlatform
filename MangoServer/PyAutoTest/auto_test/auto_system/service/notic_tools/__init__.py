# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.models import NoticeConfig
from PyAutoTest.auto_test.auto_system.service.notic_tools.sendmail import SendEmail
from PyAutoTest.auto_test.auto_system.service.notic_tools.weChatSend import WeChatSend

TYPE = {
    0: '邮箱',
    1: '企微群'
}


def notice_main(team_id, _id, case=1):
    notify_obj = NoticeConfig.objects.filter(team=team_id, id=_id)
    for i in notify_obj:
        # if i.type == TYPE.get(0) and i.state == 1:
        if i.type == 0:
            email = SendEmail(i)
            email.send_main(case)
        elif i.type == 1:
            # elif i.type == TYPE.get(1) and i.state == 1:
            wechat = WeChatSend(i)
            wechat.send_wechat_notification()
