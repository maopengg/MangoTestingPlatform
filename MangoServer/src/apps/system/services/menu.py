# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-02 19:51
# @Author : 毛鹏
import os
from copy import deepcopy

HELP_DOCUMENTATION_URL = "http://160.202.231.91:36696/"


def _two_level_routes(routes):
    """在保留页面 URL 和权限标识的前提下，按业务能力整理为两级菜单。"""

    items_by_url = {}

    def collect(items):
        for item in items:
            items_by_url[item["menuUrl"]] = item
            collect(item.get("children") or [])

    def leaf(url, parent_path, name=None, hidden=None, permission_key=None):
        item = deepcopy(items_by_url[url])
        item["parentPath"] = parent_path
        if name:
            item["menuName"] = name
        if hidden is not None:
            item["hidden"] = hidden
        if permission_key:
            item["permissionKey"] = permission_key
        item.pop("children", None)
        return item

    def group(url, name, parent_path, children, *, icon=None, is_beta=False, route_name=None):
        item = {
            "menuUrl": url,
            "menuName": name,
            "parentPath": parent_path,
            "children": children,
            "isBeta": is_beta,
        }
        if icon:
            item["icon"] = icon
        if route_name:
            item["routeName"] = route_name
        return item

    collect(routes)

    functional_test = group(
        "/functional-test",
        "研发协同",
        "/quality-management",
        [
            leaf("/functional-test/iteration/index", "/functional-test"),
            leaf("/functional-test/suite/index", "/functional-test"),
            leaf("/functional-test/design/index", "/functional-test"),
            leaf("/functional-test/case/index", "/functional-test", "测试用例"),
            leaf("/functional-test/plan/index", "/functional-test"),
            leaf("/functional-test/defect/index", "/functional-test"),
        ],
        icon="IconFile",
        is_beta=True,
    )
    report = group(
        "/report",
        "报告分析",
        "/quality-management",
        [
            leaf("/report/index", "/report"),
            leaf("/report/effectiveness/index", "/report"),
        ],
        icon="icon-calendar-clock",
    )

    ui_automation = group(
        "/uitest",
        "UI自动化",
        "/automation-test",
        [
            leaf("/uitest/page/index", "/uitest"),
            leaf("/uitest/page-steps/index", "/uitest"),
            leaf("/uitest/case/index", "/uitest"),
            leaf("/uitest/public/index", "/uitest"),
            leaf("/uitest/auth-config/index", "/uitest"),
        ],
        icon="IconFindReplace",
    )
    api_automation = group(
        "/apitest",
        "API自动化",
        "/automation-test",
        [
            leaf("/apitest/module-coverage/index", "/apitest"),
            leaf("/apitest/info/index", "/apitest", "接口管理"),
            leaf("/apitest/case/index", "/apitest"),
            leaf("/apitest/public/index", "/apitest"),
            leaf("/apitest/headers/index", "/apitest"),
            leaf("/apitest/auth-config/index", "/apitest"),
            leaf("/apitest/mock/index", "/apitest", "Mock服务"),
        ],
        icon="IconThunderbolt",
    )
    pytest_automation = group(
        "/pytest",
        "Pytest自动化",
        "/automation-test",
        [
            leaf("/pytest/repository/index", "/pytest"),
            leaf("/pytest/product/index", "/pytest"),
            leaf("/pytest/case/index", "/pytest", "Pytest用例"),
        ],
        icon="IconCodeBlock",
    )
    performance_test = group(
        "/perf",
        "性能测试",
        "/automation-test",
        [
            leaf("/perf/scenario/index", "/perf"),
            leaf("/perf/run/index", "/perf"),
            leaf("/perf/capacity/index", "/perf"),
        ],
        icon="IconDashboard",
        is_beta=True,
    )
    online_monitoring = group(
        "/monitoring",
        "监控中心",
        "/automation-test",
        [
            leaf("/monitoring/task/index", "/monitoring", "脚本运行器"),
            leaf("/monitoring/report/index", "/monitoring"),
        ],
        icon="IconPlayCircle",
    )

    data_factory = group(
        "/data-factory",
        "数据工厂",
        "/engineering-capability",
        [
            leaf("/data-factory/entity/index", "/data-factory", "数据实体"),
            leaf("/data-factory/template/index", "/data-factory"),
            leaf("/data-factory/execution/index", "/data-factory"),
        ],
        icon="IconStorage",
    )
    gray_management = group(
        "/gray",
        "灰度管理",
        "/engineering-capability",
        [
            leaf("/gray/repository/index", "/gray"),
            leaf("/gray/config-file/index", "/gray"),
            leaf("/gray/feature/index", "/gray"),
            leaf("/gray/execution-log/index", "/gray"),
        ],
        icon="IconBranch",
        is_beta=True,
    )
    test_config = group(
        "/config",
        "测试配置",
        "/engineering-capability",
        [
            leaf("/config/project/index", "/config"),
            leaf("/config/product/index", "/config", "项目与产品"),
            leaf("/config/data-source/index", "/config"),
            leaf("/config/test-object/index", "/config"),
            leaf("/config/test-files/index", "/config"),
        ],
        icon="IconCommand",
    )

    equipment_center = group(
        "/equipment",
        "设备中心",
        "/execution-scheduling",
        [leaf("/equipment/actuator/index", "/equipment", "执行器管理")],
        icon="IconMobile",
    )
    task_scheduling = group(
        "/timing",
        "任务调度",
        "/execution-scheduling",
        [
            leaf("/timing/tasks/index", "/timing"),
            leaf("/timing/strategy/index", "/timing"),
            leaf("/timing/fire-record/index", "/timing", "触发记录"),
        ],
        icon="IconSchedule",
    )

    organization_permission = group(
        "/organization-permission",
        "组织与权限",
        "/platform-management",
        [
            leaf("/organization-permission/user/index", "/organization-permission"),
            leaf("/organization-permission/role/index", "/organization-permission"),
            leaf("/organization-permission/department/index", "/organization-permission"),
        ],
        icon="IconUser",
    )
    runtime_monitoring = group(
        "/platform-management/runtime",
        "运行监控",
        "/platform-management",
        [
            leaf("/system/runtime-center/index", "/platform-management/runtime"),
            leaf("/system/error-record/index", "/platform-management/runtime"),
            leaf("/system/system-jobs/index", "/platform-management/runtime"),
            leaf("/system/execution-result/index", "/platform-management/runtime"),
        ],
    )
    audit_logs = group(
        "/platform-management/audit",
        "审计日志",
        "/platform-management",
        [
            leaf("/system/sql-execution/index", "/platform-management/audit"),
            leaf("/system/user-logs/index", "/platform-management/audit"),
        ],
    )
    help_method_children = [
        leaf("/help/variable/index", "/help/methods", "数据生成方法"),
        leaf("/help/assertion/index", "/help/methods", "断言方法"),
    ]
    help_document_children = [
        leaf(
            HELP_DOCUMENTATION_URL,
            "/help/documents",
            "使用文档",
            permission_key="help.documents",
        )
    ]
    if "/help/test" in items_by_url:
        help_document_children.append(
            leaf("/help/test", "/help/documents", hidden=True)
        )

    home = deepcopy(items_by_url["/index"])
    home["parentPath"] = ""

    top_level_groups = [
        functional_test,
        ui_automation,
        api_automation,
        pytest_automation,
        performance_test,
        deepcopy(items_by_url["/evaluation"]),
        online_monitoring,
        report,
        data_factory,
        gray_management,
        test_config,
        equipment_center,
        task_scheduling,
    ]
    for item in top_level_groups:
        item["parentPath"] = ""

    intelligent_capability = group(
        "/ai",
        "智能能力",
        "",
        [
            leaf("/ai/skill/index", "/ai"),
            leaf("/ai/mcp/index", "/ai"),
            leaf("/ai/task/index", "/ai", "AI执行记录"),
        ],
        icon="IconRobot",
        is_beta=True,
    )
    organization_permission["parentPath"] = ""
    system_operations = group(
        "/system",
        "系统运维",
        "",
        [
            leaf("/system/settings/index", "/system", "配置管理"),
            *[
                {**item, "parentPath": "/system"}
                for item in runtime_monitoring["children"]
            ],
            *[
                {**item, "parentPath": "/system"}
                for item in audit_logs["children"]
            ],
        ],
        icon="IconSettings",
        route_name="system",
    )
    help = group(
        "/help",
        "帮助与规范",
        "",
        [
            *[{**item, "parentPath": "/help"} for item in help_method_children],
            *[{**item, "parentPath": "/help"} for item in help_document_children],
        ],
        icon="IconCompass",
    )

    return [
        home,
        *top_level_groups,
        intelligent_capability,
        organization_permission,
        system_operations,
        help,
    ]


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
            "menuUrl": "/functional-test",
            "menuName": "研发协同",
            "isBeta": True,
            "icon": "IconFile",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/functional-test",
                    "menuUrl": "/functional-test/iteration/index",
                    "menuName": "迭代管理",
                    "localFilePath": "/functional-test/iteration/index",
                    "cacheable": True,
                },
                {
                    "parentPath": "/functional-test",
                    "menuUrl": "/functional-test/suite/index",
                    "menuName": "需求管理",
                    "cacheable": True,
                },
                {
                    "parentPath": "/functional-test",
                    "menuUrl": "/functional-test/design/index",
                    "menuName": "开发设计",
                    "cacheable": True,
                },
                {
                    "parentPath": "/functional-test",
                    "menuUrl": "/functional-test/case/index",
                    "menuName": "测试用例",
                    "localFilePath": "/functional-test/case-library/index",
                    "cacheable": True,
                },
                {
                    "parentPath": "/functional-test",
                    "menuUrl": "/functional-test/plan/index",
                    "menuName": "测试计划",
                    "localFilePath": "/functional-test/plan/index",
                    "cacheable": True,
                },
                {
                    "parentPath": "/functional-test",
                    "menuUrl": "/functional-test/defect/index",
                    "menuName": "缺陷管理",
                    "localFilePath": "/functional-test/defect/index",
                    "cacheable": True,
                },
            ],
        },
        {
            "menuUrl": "/uitest",
            "menuName": "UI自动化",
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
                    "menuName": "全局变量",
                    "cacheable": True,
                },
                {
                    "parentPath": "/uitest",
                    "menuUrl": "/uitest/auth-config/index",
                    "menuName": "授权管理",
                    "cacheable": True,
                },
                # {
                #     "parentPath": "/uitest",
                #     "menuUrl": "/uitest/equipment/index",
                #     "menuName": "设备配置",
                # },
            ],
        },
        {
            "menuUrl": "/apitest",
            "menuName": "API自动化",
            "icon": "IconThunderbolt",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/module-coverage/index",
                    "menuName": "模块覆盖",
                    "permissionKey": "api.module_coverage",
                    "cacheable": True,
                },
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
                    "menuName": "全局变量",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/headers/index",
                    "menuName": "请求头管理",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/auth-config/index",
                    "menuName": "授权管理",
                },
                {
                    "parentPath": "/apitest",
                    "menuUrl": "/apitest/mock/index",
                    "menuName": "Mock服务",
                    "permissionKey": "api.mock",
                },
            ],
        },
        {
            "menuUrl": "/pytest",
            "menuName": "Pytest自动化",
            "icon": "IconCodeBlock",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/repository/index",
                    "menuName": "仓库管理",
                    "permissionKey": "pytest.repository",
                },
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/product/index",
                    "menuName": "项目绑定",
                },
                {
                    "parentPath": "/pytest",
                    "menuUrl": "/pytest/case/index",
                    "menuName": "Pytest用例",
                }
            ]
        },
        {
            "menuUrl": "/monitoring",
            "menuName": "脚本运行器",
            "icon": "IconPlayCircle",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/monitoring",
                    "menuUrl": "/monitoring/task/index",
                    "menuName": "脚本运行器",
                },
                {
                    "parentPath": "/monitoring",
                    "menuUrl": "/monitoring/report/index",
                    "menuName": "预警监控报告",
                }
            ],
        },
        {
            "menuUrl": "/perf",
            "menuName": "性能测试",
            "isBeta": True,
            "icon": "IconDashboard",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/perf",
                    "menuUrl": "/perf/scenario/index",
                    "menuName": "性能场景",
                    "permissionKey": "perf.scenario",
                    "cacheable": True,
                },
                {
                    "parentPath": "/perf",
                    "menuUrl": "/perf/run/index",
                    "menuName": "运行历史",
                    "permissionKey": "perf.run",
                    "cacheable": True,
                },
                {
                    "parentPath": "/perf",
                    "menuUrl": "/perf/capacity/index",
                    "menuName": "执行器容量",
                    "permissionKey": "perf.capacity",
                    "cacheable": True,
                },
            ],
        },
        {
            "menuUrl": "/evaluation",
            "menuName": "评测中心",
            "icon": "IconExperiment",
            "parentPath": "",
            "children": [
                {"parentPath": "/evaluation", "menuUrl": "/evaluation/dataset/index", "menuName": "评测数据集", "permissionKey": "evaluation.dataset", "cacheable": True},
                {"parentPath": "/evaluation", "menuUrl": "/evaluation/case/index", "menuName": "测试用例", "permissionKey": "evaluation.case", "cacheable": True},
                {"parentPath": "/evaluation", "menuUrl": "/evaluation/grader/index", "menuName": "评分器", "permissionKey": "evaluation.grader", "cacheable": True},
            ],
        },
        {
            "menuUrl": "/data-factory",
            "menuName": "数据工厂",
            "icon": "IconStorage",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/data-factory",
                    "menuUrl": "/data-factory/entity/index",
                    "menuName": "数据实体",
                },
                {
                    "parentPath": "/data-factory",
                    "menuUrl": "/data-factory/template/index",
                    "menuName": "场景模板",
                },
                {
                    "parentPath": "/data-factory",
                    "menuUrl": "/data-factory/execution/index",
                    "menuName": "执行记录",
                },
            ],
        },
        {
            "menuUrl": "/gray",
            "menuName": "灰度管理",
            "icon": "IconBranch",
            "isBeta": True,
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/gray",
                    "menuUrl": "/gray/repository/index",
                    "menuName": "灰度仓库",
                    "permissionKey": "gray.repository",
                    "cacheable": True,
                },
                {
                    "parentPath": "/gray",
                    "menuUrl": "/gray/config-file/index",
                    "menuName": "配置文件",
                    "permissionKey": "gray.config_file",
                    "cacheable": True,
                },
                {
                    "parentPath": "/gray",
                    "menuUrl": "/gray/feature/index",
                    "menuName": "灰度开关",
                    "permissionKey": "gray.feature",
                    "cacheable": True,
                },
                {
                    "parentPath": "/gray",
                    "menuUrl": "/gray/execution-log/index",
                    "menuName": "执行记录",
                    "permissionKey": "gray.execution_log",
                    "cacheable": True,
                },
            ],
        },
        {
            "menuUrl": "/report",
            "menuName": "质量报告",
            "icon": "icon-calendar-clock",
            "children": [
                {
                    "parentPath": "/report",
                    "menuUrl": "/report/index",
                    "menuName": "执行报告",
                },
                {
                    "parentPath": "/report",
                    "menuUrl": "/report/effectiveness/index",
                    "menuName": "质量效能",
                    "permissionKey": "report.effectiveness",
                    "cacheable": True,
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
                    "menuUrl": "/config/data-source/index",
                    "menuName": "数据库配置",
                    "permissionKey": "config.datasource",
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
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/system-jobs/index",
                    "menuName": "系统定时任务",
                    "localFilePath": "/timing/system-jobs/index",
                    "permissionKey": "timing.system_jobs",
                },
            ],
        },
        {
            "menuUrl": "/ai",
            "menuName": "AI",
            "isBeta": True,
            "icon": "IconRobot",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/ai",
                    "menuUrl": "/ai/skill/index",
                    "menuName": "技能管理",
                },
                {
                    "parentPath": "/ai",
                    "menuUrl": "/ai/mcp/index",
                    "menuName": "MCP服务",
                },
                {
                    "parentPath": "/ai",
                    "menuUrl": "/ai/task/index",
                    "menuName": "执行记录",
                },
            ],
        },
        {
            "menuUrl": "/organization-permission",
            "menuName": "组织权限",
            "icon": "IconUser",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/organization-permission",
                    "menuUrl": "/organization-permission/user/index",
                    "menuName": "用户管理",
                    "routeName": "user",
                    "localFilePath": "/system/user/index",
                    "permissionKey": "system.user",
                },
                {
                    "parentPath": "/organization-permission",
                    "menuUrl": "/organization-permission/role/index",
                    "menuName": "角色管理",
                    "localFilePath": "/system/role/index",
                    "permissionKey": "system.role",
                },
                {
                    "parentPath": "/organization-permission",
                    "menuUrl": "/organization-permission/department/index",
                    "menuName": "部门管理",
                    "localFilePath": "/system/department/index",
                    "permissionKey": "system.department",
                },
            ],
        },
        {
            "menuUrl": "/system",
            "menuName": "系统运维",
            "icon": "IconSettings",
            "parentPath": "",
            "routeName": "system",
            "children": [
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/settings/index",
                    "menuName": "配置管理",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/runtime-center/index",
                    "menuName": "运行中心",
                },
                {
                    "parentPath": "/timing",
                    "menuUrl": "/timing/fire-record/index",
                    "menuName": "触发记录",
                    "localFilePath": "/system/fire-record/index",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/execution-result/index",
                    "menuName": "自动化执行结果",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/sql-execution/index",
                    "menuName": "SQL执行记录",
                    "permissionKey": "system.sql_execution",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/error-record/index",
                    "menuName": "系统异常记录",
                    "permissionKey": "system.error_record",
                },
                {
                    "parentPath": "/system",
                    "menuUrl": "/system/user-logs/index",
                    "menuName": "操作日志",
                }
            ],
        },
        {
            "menuUrl": "/help",
            "menuName": "帮助",
            "icon": "IconCompass",
            "parentPath": "",
            "children": [
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/variable/index",
                    "menuName": "测试数据方法",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": "/help/assertion/index",
                    "menuName": "用例断言方法",
                },
                {
                    "parentPath": "/help",
                    "menuUrl": HELP_DOCUMENTATION_URL,
                    "menuName": "帮助文档",
                },
            ],
        },
    ]
    if os.getenv('DJANGO_ENV') == 'dev':
        menu[-1]['children'].append({
            "parentPath": "/help",
            "menuUrl": "/help/test",
            "menuName": "测试页面",
        })
    return _two_level_routes(menu)
