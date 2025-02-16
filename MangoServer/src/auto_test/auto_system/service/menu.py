# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-02 19:51
# @Author : 毛鹏
import os


def ad_routes():
    """菜单模拟数据"""
    menu = [
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
                },
            ],
        },
        {
            "menuUrl": "/apitest",
            "menuName": "接口自动化",
            "icon": "IconSend",
            "parentPath": "",
            "children": [
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
                    "menuUrl": "/apitest/headers/index",
                    "menuName": "请求头管理",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/public/index",
                    "menuName": "公共参数",
                },
            ],
        },
        {
            "menuUrl": "/pytest",
            "menuName": "mango_pytest",
            "icon": "icon-calendar-clock",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/api-init/index",
                    "menuName": "API初始化",
                },
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/api-api-info/index",
                    "menuName": "API接口",
                },
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/api-api-file/index",
                    "menuName": "测试文件",
                },
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/api-case/index",
                    "menuName": "API用例",
                },
            ]
        },
        {
            "menuUrl": "/report",
            "menuName": "测试报告",
            "icon": "icon-calendar-clock",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/report",
                    "menuUrl": "/report/index",
                    "menuName": "测试报告",
                },
            ]
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
                    "menuUrl": "/config/test-files/index",
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
                    "menuUrl": "/timing/tasks/index",
                    "menuName": "定时任务",
                },
                {
                    "parentPath": "/timing",
                    "menuUrl": "/timing/strategy/index",
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
                    "menuUrl": "http://121.37.174.56:8002/",
                    "menuName": "帮助文档",
                },
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
            ],
        },
    ]
    if os.getenv('DJANGO_ENV') == 'dev' or os.getenv('DJANGO_ENV') == 'test':
        menu[-1]['children'].append({
            "parentPath": "/help",
            "menuUrl": "/help/test",
            "menuName": "测试页面",
        })
    return menu
