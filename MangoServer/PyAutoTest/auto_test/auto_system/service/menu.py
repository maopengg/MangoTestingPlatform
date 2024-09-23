# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-02 19:51
# @Author : 毛鹏
def ad_routes():
    """菜单模拟数据"""
    return [
        {
            "menuUrl": "/index",
            "menuName": "首页",
            "icon": "SettingIcon",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/index",
                    "menuUrl": "/index/home",
                    "menuName": "首页",
                }
            ],
        },
        {
            "menuUrl": "/uitest",
            "menuName": "前端自动化",
            "icon": "IconFindReplace",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/page/index",
                    "menuName": "页面元素",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/page-steps/index",
                    "menuName": "页面步骤",
                    "cacheable": True,
                }, {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/case/index",
                    "menuName": "测试用例",
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/public/index",
                    "menuName": "公共参数",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/equipment/index",
                    "menuName": "设备配置",
                }, {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/report/index",
                    "menuName": "测试报告",
                },
            ],
        },
        {
            "menuUrl": "/apitest",
            "menuName": "接口自动化",
            "icon": "IconSend",
            "parentPath": "",
            "children": [
                # {
                #     "parentPath": "/apitest",
                #     "menuUrl": "/apitest/mock",
                #     "menuName": "Mock服务",
                # },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/info/index",
                    "menuName": "接口管理",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/case/index",
                    "menuName": "测试用例",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/public/index",
                    "menuName": "公共参数",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/report/index",
                    "menuName": "测试报告",
                },
            ],
        },
        # {
        #     "menuUrl": "/perf",
        #     "menuName": "性能自动化",
        #     "icon": "IconMinus",
        #     "parentPath": "",
        #     "children": [
        #         {
        #             "parentPath": "/perf",
        #             "menuUrl": "/perf/prepare",
        #             "menuName": "接口准备",
        #         },
        #         {
        #             "parentPath": "/perf",
        #             "menuUrl": "/perf/report",
        #             "menuName": "测试报告",
        #         },
        #     ],
        # },
        {
            "menuUrl": "/equipment",
            "menuName": "设备中心",
            "icon": "IconMobile",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/equipment",
                    "menuUrl": "/equipment/actuator/index",
                    "menuName": "执行器",
                }
            ],
        },
        {
            "menuUrl": "/config",
            "menuName": "测试配置",
            "icon": "IconCommand",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/project/index",
                    "menuName": "项目配置",
                }, {
                    "parentPath": "/config",
                    "menuUrl": "/config/product/index",
                    "menuName": "项目产品",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/test-object/index",
                    "menuName": "测试对象",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/database/index",
                    "menuName": "数据库配置",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/notice/index",
                    "menuName": "通知配置",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/text.txt-files/index",
                    "menuName": "测试文件",
                }
            ],
        },

        {
            "menuUrl": "/timing",
            "menuName": "定时任务",
            "icon": "IconSchedule",
            "children": [
                {
                    "parentPath": "/timing",
                    "menuUrl": "/timing/strategy/index",
                    "menuName": "定时策略",
                },
                {
                    "parentPath": "/timing",
                    "menuUrl": "/timing/scheduled-tasks/index",
                    "menuName": "定时任务",
                },

            ],
        },
        {
            "menuUrl": "/system",
            "menuName": "系统管理",
            "icon": "IconSettings",
            "parentPath": "",
            "routeName": "system",
            "children": [
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/settings/index",
                    "menuName": "系统设置",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/user/index",
                    "menuName": "用户管理",
                    "badge": "dot",
                    "routeName": "user",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/role/index",
                    "menuName": "角色管理",
                    "badge": "12",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/user-logs/index",
                    "menuName": "登录日志",
                    "badge": "13",
                }
                # {
                #     "parentPath": "/system",
                #     "menuUrl": "/system/menu",
                #     "menuName": "菜单管理",
                # },
            ],
        },
        {
            "menuUrl": "/help",
            "menuName": "帮助",
            "badge": "dot",
            "icon": "IconCompass",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/variable/index",
                    "menuName": "公共变量",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/assertion/index",
                    "menuName": "断言策略",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "http://121.37.174.56:8002/",
                    "menuName": "使用手册",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/text.txt",
                    "menuName": "测试页面",
                },
            ],
        },
    ]
