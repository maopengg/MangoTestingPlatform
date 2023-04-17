# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-15 23:07
# @Author : 毛鹏
import asyncio

import notification_send
from auto_ui.test_result.test_report_return import TestReportReturn


class ResultMain(TestReportReturn):
    res_data = []

    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

    def res_collect(self):
        # self.res_data.append()
        pass

    async def res_dispatch(self):
        await asyncio.gather(self.notification_send(),
                             self.test_res_analysis())

    async def notification_send(self):
        await notification_send.email_send(code=self.code, msg=self.msg)

    @classmethod
    async def test_res_analysis(cls):
        return await cls.ele_res_insert(
            ele_name='新增商品按钮',
            existence=1,
            state=0,
            case_id='新建普通商品',
            case_group_id='null',
            team_id='应用组',
            test_obj_id='zshop预发环境',
            msg='元素不存在',
            picture='www.baidu.com'
        )


if __name__ == '__main__':
    code = 200
    msg = 'haah'
    r = ResultMain(code, msg)
    asyncio.run(r.res_dispatch())
