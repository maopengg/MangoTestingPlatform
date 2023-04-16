# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-15 23:07
# @Author : 毛鹏

from auto_ui.test_result.notification_send import NotificationSend
from auto_ui.test_result.test_report_return import TestReportReturn


class ResultMain(TestReportReturn, NotificationSend):
    res_data = [
        {
            "case_id": "打开生产环境常规小程序",
            "case_name": "打开生产环境常规小程序",
            "case_url": "com.tencent.mm-",
            "equipment": "8796a033",
            "package": "com.tencent.mm",
            "type": 1,
            "": '',
            "case_data": [
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序",
                    "ele_page_name": "微信",
                    "ele_exp": None,
                    "ele_loc": None,
                    "ele_sleep": 3,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "微信首页搜索按钮",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@resource-id=\"com.tencent.mm:id/j5t\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 2,
                    "ass_type": 0,
                    "ope_value": "卓尔数科常规生产",
                    "ass_value": None,
                    "ele_name": "微信首页搜索输入框",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@resource-id=\"com.tencent.mm:id/j4t\"]/android.widget.RelativeLayout[1]",
                    "ele_sleep": 2,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "点击搜索到的小程序",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@resource-id=\"com.tencent.mm:id/a27\"]",
                    "ele_sleep": 5,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序分类tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "/html/body/wx-view/wx-z-tab-bar/wx-view/wx-view[2]/wx-view/wx-view[2]/wx-view/wx-view[1]/wx-view/wx-view/wx-view[1]/wx-image/div",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序内容中心tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"内容中心\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序购物车tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"购物车\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序我的tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//*[@text=\"我的\"]",
                    "ele_sleep": None,
                    "ele_sub": None
                },
                {
                    "ope_type": 1,
                    "ass_type": 0,
                    "ope_value": None,
                    "ass_value": None,
                    "ele_name": "小程序首页tab",
                    "ele_page_name": "微信",
                    "ele_exp": 0,
                    "ele_loc": "//android.webkit.WebView/android.view.View[6]/android.view.View[1]/android.widget.TextView[1]",
                    "ele_sleep": None,
                    "ele_sub": None
                }
            ]
        }
    ]

    # 第一个列表是用例组，套

    def res_collect(self):
        # self.res_data.append()
        pass

    #
    # async def res_dispatch(self):
    #     await asyncio.gather(self.notification_send(),
    #                          self.test_res_analysis())

    async def notification_send(self):
        pass

    @classmethod
    def test_res_analysis(cls):
        # sql = "INSERT INTO ui_result (ele_name, existence, state, case_id, case_group_id, team_id, test_obj_id, msg, picture) VALUES ('新增商品按钮', 1, 0, '新建普通商品',null,'应用组', 'zshop预发环境', '元素不存在', 'www.baidu.com' );"
        return cls.ele_res_insert(
            ele_name='新增商品按钮',
            existence=1,
            state=0,
            case_id='新建普通商品',
            case_group_id=None,
            team_id='应用组',
            test_obj_id='zshop预发环境',
            msg='元素不存在',
            picture='www.baidu.com'
        )


if __name__ == '__main__':
    r = ResultMain.test_res_analysis()
    print(r)
