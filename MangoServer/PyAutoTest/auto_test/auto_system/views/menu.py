# -*- coding: utf-8 -*-
# @Project: MangoServer
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
            "menuName": "界面自动化",
            "icon": "IconFindReplace",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/page",
                    "menuName": "页面元素",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/page-steps",
                    "menuName": "页面步骤",
                    "cacheable": True,
                }, {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-case",
                    "menuName": "测试用例",
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-public",
                    "menuName": "公共参数",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/equipment-config",
                    "menuName": "设备配置",
                }, {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-test-report",
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
                    "menuUrl": "/apitest/api-info",
                    "menuName": "接口信息",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-case",
                    "menuName": "测试用例",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-public",
                    "menuName": "公共方法",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-test-report",
                    "menuName": "测试报告",
                },
            ],
        },
        # {
        #     "menuUrl": "/data_producer",
        #     "menuName": "性能自动化",
        #     "icon": "IconMinus",
        #     "parentPath": "",
        #     "children": [
        #         {
        #             "parentPath": "/data_producer",
        #             "menuUrl": "/data_producer/prepare",
        #             "menuName": "接口准备",
        #         },
        #         {
        #             "parentPath": "/data_producer",
        #             "menuUrl": "/data_producer/report",
        #             "menuName": "测试报告",
        #         },
        #     ],
        # },
        # {
        #     "menuUrl": "/equipment",
        #     "menuName": "设备中心",
        #     "icon": "IconMobile",
        #     "parentPath": "",
        #     "children": [
        #         {
        #             "parentPath": "/equipment",
        #             "menuUrl": "/equipment/actuator",
        #             "menuName": "执行器",
        #         }
        #     ],
        # },
        {
            "menuUrl": "/config",
            "menuName": "测试配置",
            "icon": "IconCommand",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/project",
                    "menuName": "测试项目",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/test-obj",
                    "menuName": "测试环境",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/database",
                    "menuName": "数据库配置",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/notice",
                    "menuName": "通知配置",
                },
                {
                    "parentPath": "/config",
                    "menuUrl": "/config/test-files",
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
                    "menuUrl": "/timing/scheduled-tasks",
                    "menuName": "定时任务",
                },
                {
                    "parentPath": "/timing",
                    "menuUrl": "/timing/programme",
                    "menuName": "定时策略",
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
                    "menuUrl": "/system/settings",
                    "menuName": "系统设置",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/user",
                    "menuName": "用户管理",
                    "badge": "dot",
                    "routeName": "user",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/role",
                    "menuName": "角色管理",
                    "badge": "12",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/user-logs",
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
                    "menuUrl": "/help/variable",
                    "menuName": "公共变量",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/assertion",
                    "menuName": "断言策略",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/manual",
                    "menuName": "使用手册",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/test",
                    "menuName": "vue测试页面",
                },
            ],
        },
    ]
