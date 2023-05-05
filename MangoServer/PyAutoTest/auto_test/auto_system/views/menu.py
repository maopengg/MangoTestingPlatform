# -*- coding: utf-8 -*-
# @Project: auto_test
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
                    "menuName": "数据看板",
                },
                # {
                #     "parentPath": "/index",
                #     "menuUrl": "/index/work-place",
                #     "menuName": "个人中心",
                # },
            ],
        },
        {
            "menuUrl": "/apitest",
            "menuName": "Api自动化",
            "icon": "IconSend",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/postman",
                    "menuName": "PostMan",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/mock",
                    "menuName": "Mock服务",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-case-debug",
                    "menuName": "调试用例",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-case-group",
                    "menuName": "测试用例组",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-public",
                    "menuName": "公共方法",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/api-test-result",
                    "menuName": "测试报告",
                },
            ],
        },
        {
            "menuUrl": "/uitest",
            "menuName": "Ui自动化",
            "icon": "IconFindReplace",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/page-obj",
                    "menuName": "页面对象",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-case-debug",
                    "menuName": "调试用例",
                    "cacheable": True,
                }, {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-case-group",
                    "menuName": "测试用例组",
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-public",
                    "menuName": "公共方法",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-test-result",
                    "menuName": "测试报告",
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/ui-config",
                    "menuName": "配置与元素收集",
                }
            ],
        },
        {
            "menuUrl": "/perf",
            "menuName": "性能测试",
            "icon": "IconMinus",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/perf",
                    "menuUrl": "/perf/prepare",
                    "menuName": "接口准备",
                },
                {
                    "parentPath": "/perf",
                    "menuUrl": "/perf/report",
                    "menuName": "测试报告",
                },
            ],
        },
        {
            "menuUrl": "/equipment",
            "menuName": "设备中心",
            "icon": "IconMobile",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/equipment",
                    "menuUrl": "/equipment/actuator",
                    "menuName": "执行器",
                }
            ],
        },
        {
            "menuUrl": "/testconfig",
            "menuName": "测试配置",
            "icon": "IconCommand",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/testconfig",
                    "menuUrl": "/testconfig/test_obj",
                    "menuName": "测试对象",
                },
                {
                    "parentPath": "/testconfig",
                    "menuUrl": "/testconfig/database",
                    "menuName": "数据库配置",
                },
                {
                    "parentPath": "/testconfig",
                    "menuUrl": "/testconfig/notice",
                    "menuName": "通知配置",
                }
            ],
        },

        {
            "menuUrl": "/timing",
            "menuName": "定时任务",
            "icon": "IconSchedule",
            "children": [
                # {
                #     "parentPath": "/timing",
                #     "menuUrl": "/timing/dispatch",
                #     "menuName": "调度中心",
                # },
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
                    "menuUrl": "/system/department",
                    "menuName": "项目管理",
                    "badge": "new",
                    "routeName": "department",
                    "localFilePath": "/system/local-path/department",
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
                    "menuUrl": "/system/menu",
                    "menuName": "菜单管理",
                },
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
                    "menuUrl": "/help/thank",
                    "menuName": "致谢",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/test",
                    "menuName": "vue测试页面",
                },
            ],
        },
    ]


def data_list():
    """表格搜索模拟数据"""
    return {
        "totalSize": 30,
        "code": 200,
        "msg": "操作成功",
        "data": [
            {
                "id": 1,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 1,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 0,
                "nickName": "Scott Garcia",
                "lastLoginIp": "96.208.134.239"
            },
            {
                "id": 2,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 5,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 1,
                "nickName": "Charles Lopez",
                "lastLoginIp": "207.213.193.118"
            },
            {
                "id": 3,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 1,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 0,
                "nickName": "Anthony Anderson",
                "lastLoginIp": "105.12.233.168"
            },
            {
                "id": 4,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 4,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 1,
                "nickName": "Sarah Taylor",
                "lastLoginIp": "133.181.111.196"
            },
            {
                "id": 5,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 1,
                "nickName": "Joseph Rodriguez",
                "lastLoginIp": "214.237.37.182"
            },
            {
                "id": 6,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 0,
                "nickName": "Barbara Hernandez",
                "lastLoginIp": "96.228.21.103"
            },
            {
                "id": 7,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 1,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 0,
                "nickName": "Thomas Lee",
                "lastLoginIp": "149.66.30.70"
            },
            {
                "id": 8,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 5,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 1,
                "nickName": "Karen Brown",
                "lastLoginIp": "127.201.71.104"
            },
            {
                "id": 9,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 1,
                "nickName": "Timothy Thompson",
                "lastLoginIp": "109.66.155.196"
            },
            {
                "id": 10,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 4,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:56:20",
                "status": 1,
                "nickName": "Steven Brown",
                "lastLoginIp": "6.229.252.56"
            }
        ]
    }


def department():
    """部门管理模拟数据"""
    return {
        "code": 200,
        "msg": "操作成功",
        "data": [
            {
                "id": 1,
                "name": "总裁办",
                "depCode": "dp_code_manager",
                "order": 1,
                "createTime": "2023-02-05 19:54:06",
                "status": 0
            },
            {
                "id": 2,
                "name": "市场部",
                "depCode": "dp_code_marketing",
                "order": 1,
                "createTime": "2023-02-05 19:54:06",
                "status": 1,
                "children": [
                    {
                        "id": 3,
                        "name": "市场一部",
                        "depCode": "dp_code_marketing_1",
                        "order": 1,
                        "createTime": "2023-02-05 19:54:06",
                        "status": 1
                    },
                    {
                        "id": 4,
                        "name": "市场二部",
                        "depCode": "dp_code_marketing_2",
                        "order": 1,
                        "createTime": "2023-02-05 19:54:06",
                        "status": 1
                    }
                ]
            },
            {
                "id": 5,
                "name": "技术部",
                "depCode": "dp_code_technology",
                "order": 1,
                "createTime": "2023-02-05 19:54:06",
                "status": 1
            },
            {
                "id": 6,
                "name": "销售部",
                "depCode": "dp_code_sale",
                "order": 1,
                "createTime": "2023-02-05 19:54:06",
                "status": 1
            }
        ]
    }


def user():
    """用户管理模拟数据"""
    return {
        "totalSize": 30,
        "code": 200,
        "msg": "操作成功",
        "data": [
            {
                "id": 1,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 1,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "Michael Young",
                "lastLoginIp": "159.31.199.53"
            },
            {
                "id": 2,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 4,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "Sarah Walker",
                "lastLoginIp": "5.86.96.50"
            },
            {
                "id": 3,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "Michelle Gonzalez",
                "lastLoginIp": "169.196.59.207"
            },
            {
                "id": 4,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 4,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 1,
                "nickName": "Gary Walker",
                "lastLoginIp": "203.7.51.61"
            },
            {
                "id": 5,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "Jessica Davis",
                "lastLoginIp": "7.79.8.167"
            },
            {
                "id": 6,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 0,
                "departmentName": "研发部",
                "departmentId": 6,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "Anthony Anderson",
                "lastLoginIp": "232.39.112.59"
            },
            {
                "id": 7,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 1,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "John Rodriguez",
                "lastLoginIp": "39.167.75.68"
            },
            {
                "id": 8,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 3,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "John Anderson",
                "lastLoginIp": "186.230.29.57"
            },
            {
                "id": 9,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 4,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 0,
                "nickName": "Nancy Johnson",
                "lastLoginIp": "59.179.220.126"
            },
            {
                "id": 10,
                "avatar": "@assets/img_avatar_01.jpeg",
                "mobile": "18800000000",
                "email": "123456@163.com",
                "gender": 1,
                "departmentName": "研发部",
                "departmentId": 2,
                "roleName": "超级管理员",
                "roleId": 2,
                "lastLoginTime": "2023-02-05 19:54:22",
                "status": 1,
                "nickName": "Maria Jackson",
                "lastLoginIp": "183.19.54.226"
            }
        ]
    }


def role():
    """角色管理模拟数据"""
    return {
        "code": 200,
        "msg": "获取数据成功",
        "data": [
            {
                "id": 1,
                "name": "超级管理员",
                "roleCode": "ROLE_admin",
                "description": "超级管理员",
                "createTime": "2023-02-05 19:54:36"
            },
            {
                "id": 2,
                "name": "编辑员",
                "roleCode": "ROLE_editor",
                "description": "编辑员",
                "createTime": "2023-02-05 19:54:36"
            }
        ]
    }


def menu_():
    """菜单管理模拟数据"""
    return {
        "code": 200,
        "msg": "获取菜单列表成功",
        "data": [
            {
                "menuUrl": "/system",
                "menuName": "系统管理",
                "icon": "SettingIcon",
                "tip": "new",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/system",
                        "menuUrl": "/system/department",
                        "menuName": "部门管理",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/system",
                        "menuUrl": "/system/user",
                        "menuName": "用户管理",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/system",
                        "menuUrl": "/system/role",
                        "menuName": "角色管理",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/system",
                        "menuUrl": "/system/menu",
                        "menuName": "菜单管理",
                        "cacheable": True,
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/list",
                "menuName": "列表页面",
                "icon": "OperationIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/list",
                        "menuUrl": "/list/table-with-search",
                        "menuName": "表格搜索",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/list",
                        "menuUrl": "/list/table-custom",
                        "menuName": "自定义表格",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/list",
                        "menuUrl": "/list/list",
                        "menuName": "普通列表",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/list",
                        "menuUrl": "/list/card-list",
                        "menuName": "卡片列表",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/form",
                "menuName": "表单页面",
                "tip": "dot",
                "icon": "PostcardIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/form",
                        "menuUrl": "/form/base-form-view",
                        "menuName": "基本表单",
                        "cacheable": True,
                        "isSelect": True
                    },
                    {
                        "parentPath": "/form",
                        "menuUrl": "/form/advance-form",
                        "menuName": "高级表单",
                        "cacheable": True,
                        "isSelect": True
                    },
                    {
                        "parentPath": "/form",
                        "menuUrl": "/form/step-form",
                        "menuName": "分步表单",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/form",
                        "menuUrl": "/form/form-component",
                        "menuName": "表单组件",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/other",
                "menuName": "功能/组件",
                "icon": "GridIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/chart",
                        "menuName": "图表",
                        "children": [
                            {
                                "parentPath": "/other/chart",
                                "menuUrl": "/other/chart/icon",
                                "menuName": "图标",
                                "children": [
                                    {
                                        "parentPath": "/other/chart",
                                        "menuUrl": "/other/chart/icon/icon-font",
                                        "menuName": "IconFont"
                                    },
                                    {
                                        "parentPath": "/other/chart",
                                        "menuUrl": "/other/chart/icon/element-plus",
                                        "menuName": "ElementPlus"
                                    },
                                    {
                                        "parentPath": "/other/chart",
                                        "menuUrl": "/other/chart/icon/icon-select",
                                        "menuName": "图标选择器"
                                    }
                                ]
                            },
                            {
                                "parentPath": "/other/chart",
                                "menuUrl": "/other/chart/echarts",
                                "menuName": "echarts"
                            }
                        ],
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/print",
                        "menuName": "打印",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/tip",
                        "menuName": "消息提示",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/clipboard",
                        "menuName": "剪切板",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "http://www.vueadminwork.com",
                        "menuName": "外链",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/cropper",
                        "menuName": "图片裁剪",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/qrcode",
                        "menuName": "二维码",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/css-animation",
                        "menuName": "Css动画",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/other",
                        "menuUrl": "/other/descriptions",
                        "menuName": "详情页面",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/result",
                "menuName": "结果页面",
                "icon": "TakeawayBoxIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/result",
                        "menuUrl": "/result/success",
                        "menuName": "成功页面",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/result",
                        "menuUrl": "/result/fail",
                        "menuName": "失败页面",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/exception",
                "menuName": "异常页面",
                "icon": "WarningIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/exception",
                        "menuUrl": "/exception/404",
                        "menuName": "404页面",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/exception",
                        "menuUrl": "/exception/403",
                        "menuName": "403页面",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/exception",
                        "menuUrl": "/exception/500",
                        "menuName": "500页面",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/editor",
                "menuName": "编辑器",
                "tip": "12",
                "icon": "EditIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/editor",
                        "menuUrl": "/editor/rich-text",
                        "menuName": "富文本",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/editor",
                        "menuUrl": "/editor/markdown",
                        "menuName": "markdown",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/excel",
                "menuName": "Excel",
                "icon": "NotebookIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/excel",
                        "menuUrl": "/excel/export-excel",
                        "menuName": "导出Excel",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/excel",
                        "menuUrl": "/excel/export-rows-excel",
                        "menuName": "导出选中行",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/draggable",
                "menuName": "拖拽",
                "icon": "PointerIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/draggable",
                        "menuUrl": "/draggable/dialog-draggable",
                        "menuName": "拖拽对话框",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/draggable",
                        "menuUrl": "/draggable/card-draggable",
                        "menuName": "卡片拖拽",
                        "cacheable": True,
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/next",
                "menuName": "多级菜单",
                "icon": "ShareIcon",
                "parentPath": "",
                "children": [
                    {
                        "parentPath": "/next",
                        "menuUrl": "/next/menu1",
                        "menuName": "menu-1",
                        "cacheable": True,
                        "isSelect": True
                    },
                    {
                        "parentPath": "/next",
                        "menuUrl": "/next/menu2",
                        "menuName": "menu-2",
                        "children": [
                            {
                                "parentPath": "/next/menu2",
                                "menuUrl": "/next/menu2/menu-2-1",
                                "menuName": "menu-2-1",
                                "children": [
                                    {
                                        "parentPath": "/next/menu2/menu-2-1",
                                        "menuUrl": "/next/menu2/menu-2-1/menu-2-1-1",
                                        "menuName": "menu-2-1-1",
                                        "cacheable": True
                                    },
                                    {
                                        "parentPath": "/next/menu2/menu-2-1",
                                        "menuUrl": "/next/menu2/menu-2-1/menu-2-1-2",
                                        "menuName": "menu-2-1-2"
                                    }
                                ]
                            },
                            {
                                "parentPath": "/next/menu2",
                                "menuUrl": "/next/menu2/menu-2-2",
                                "menuName": "menu-2-2",
                                "cacheable": True
                            }
                        ],
                        "isSelect": True
                    }
                ],
                "isSelect": True
            },
            {
                "menuUrl": "/map",
                "menuName": "地图",
                "icon": "MapLocationIcon",
                "children": [
                    {
                        "parentPath": "/map",
                        "menuUrl": "/map/gaode",
                        "menuName": "高德地图",
                        "isSelect": True
                    },
                    {
                        "parentPath": "/map",
                        "menuUrl": "/map/baidu",
                        "menuName": "百度地图",
                        "isSelect": True
                    }
                ],
                "isSelect": True
            }
        ]
    }
