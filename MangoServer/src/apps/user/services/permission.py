from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable

from django.db import transaction

from src.apps.system.services.menu import ad_routes
from src.apps.user.constants import GUEST_DENIED_ACTION_KEYS, STATUS_PERMISSION_FIELDS
from src.apps.user.models import (
    DepartmentProjectProductPermission,
    Role,
    RoleMenuPermission,
    User,
    UserDepartment,
)

GUEST_ROLE_NAME = '游客'
HOME_PERMISSION_KEY = 'index.home'
GUEST_DENIED_PAGE_PREFIXES = ('system.',)
GUEST_DENIED_PAGE_KEYS = {'system', 'gray'}
GUEST_ALLOWED_ACTIONS = {'detail', 'debug', 'execute', 'download', 'export', 'query', 'retry', 'notice'}


@dataclass
class AuthUserContext(dict):
    """兼容旧 dict 用法，同时给 DRF 权限提供真实用户对象。"""

    user: User

    def __post_init__(self):
        super().__init__(
            id=self.user.id,
            username=self.user.username,
            name=self.user.name,
            role_id=self.user.role_id,
            is_super_admin=self.user.is_super_admin,
        )

    @property
    def is_authenticated(self):
        return True

    @property
    def user_obj(self) -> User:
        return self.user

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as error:
            raise AttributeError(item) from error


class PermissionMenuService:
    ACTION_LABELS = {
        'import': '导入',
        'create': '新增',
        'edit': '编辑',
        'delete': '删除',
        'detail': '详情',
        'execute': '执行',
        'debug': '调试',
        'export': '导出',
        'download': '下载',
        'notice': '通知',
        'retry': '重试',
        'exclude': '排查与排除',
        'copy': '复制',
        'publish': '发布',
        'status': '状态变更',
        'query': '查询',
        'sync-library': '同步用例库',
        'stop': '停止',
        'baseline': '设置基线',
        'submit': '提交',
        'bind_functional': '绑定功能依据',
    }
    ACTION_DESCRIPTIONS = {
        'import': '允许校验、预览并导入数据。',
        'create': '允许创建当前页面相关数据，包括新增、导入、上传、批量生成等写入操作。',
        'edit': '允许修改当前页面已有数据，包括编辑、保存、同步、排序、绑定、更新目录等操作。',
        'delete': '允许删除当前页面数据，包含批量删除、清理、解绑等危险操作。',
        'detail': '允许查看详情、文件、日志、步骤、配置、关联数据等更完整的信息。',
        'execute': '允许触发执行类动作，例如运行用例、启动任务、拉取代码、推送代码或触发系统定时任务。',
        'debug': '允许调试、测试连接、刷新缓存、生成预览数据等排查类操作。',
        'export': '允许导出当前页面数据或报告文件。',
        'download': '允许下载模板、日志、文件或报告附件。',
        'notice': '允许发送通知消息。',
        'retry': '允许重试失败任务、报告或用例。',
        'exclude': '允许填写报告失败原因、排除或恢复执行项统计。',
        'copy': '允许复制当前数据并生成新记录。',
        'publish': '允许发布、升级或回退当前页面的版本。',
        'status': '允许切换启用状态、发布状态、刷新状态或其他状态类字段。',
        'query': '允许执行查询类操作，例如逻辑数据库 SQL 查询。',
        'sync-library': '允许将执行数据同步或保存到用例库。',
        'stop': '允许停止或取消当前页面的运行任务。',
        'baseline': '允许将当前结果设置为比较基线。',
        'submit': '允许提交当前页面的复核或审批结果。',
        'bind_functional': '允许确认或更新功能用例与覆盖对象的核验关系。',
    }
    ACTION_DESCRIPTION_OVERRIDES = {
        'api.info:create': '允许新增、导入、录制或批量导入接口定义。',
        'api.info:detail': '允许查看接口详情、接口步骤和关联配置。',
        'api.info:debug': '允许单接口调试、并发调试和接口数据排查。',
        'api.info:execute': '允许批量执行接口管理中的接口。',
        'api.info:download': '允许下载接口导入模板。',
        'api.info:publish': '允许发布或恢复 API 接口版本。',
        'api.case:create': '允许新增 API 用例、增加步骤或增加场景参数。',
        'api.case:edit': '允许编辑 API 用例、同步步骤、设置套件和调整排序。',
        'api.case:detail': '允许查看 API 用例步骤、场景和执行详情。',
        'api.case:debug': '允许调试 API 用例参数提取和执行过程。',
        'api.case:execute': '允许执行单个或批量 API 用例。',
        'api.case:copy': '允许复制 API 用例或场景参数。',
        'api.case:publish': '允许发布、升级或回退 API 用例版本。',
        'api.auth_config:detail': '允许查看授权配置详情和缓存内容。',
        'api.auth_config:debug': '允许刷新、清空或测试授权缓存。',
        'api.public:status': '允许启用或停用 API 全局变量。',
        'api.headers:status': '允许启用或停用请求头配置。',
        'ui.page:create': '允许新增页面、上传元素或单个新增元素。',
        'ui.page:edit': '允许编辑页面、元素、iframe 设置和元素修复结果。',
        'ui.page:detail': '允许查看页面元素、元素详情和关联步骤。',
        'ui.page:debug': '允许调试页面元素定位和打开新浏览器对象。',
        'ui.page:download': '允许下载 UI 元素导入模板。',
        'ui.page_steps:create': '允许新增页面步骤和步骤明细。',
        'ui.page_steps:edit': '允许编辑页面步骤、步骤明细和调整步骤排序。',
        'ui.page_steps:detail': '允许查看页面步骤详情、操作类型和断言配置。',
        'ui.page_steps:debug': '允许调试页面步骤执行。',
        'ui.case:create': '允许新增 UI 用例和增加用例步骤。',
        'ui.case:edit': '允许编辑 UI 用例、同步步骤、设置套件和绑定步骤。',
        'ui.case:detail': '允许查看 UI 用例步骤、套件和执行详情。',
        'ui.case:execute': '允许执行单个或批量 UI 用例。',
        'ui.case:copy': '允许复制 UI 用例。',
        'ui.case:publish': '允许提交 UI 用例预发布，由产品负责人通过发布或退回未发布。',
        'ui.auth_config:detail': '允许查看 UI 授权缓存和配置详情。',
        'ui.auth_config:debug': '允许刷新、清空、自动授权或完成登录采集。',
        'ui.public:status': '允许启用或停用 UI 全局变量。',
        'pytest.product:detail': '允许读取 pytest 项目文件和绑定详情。',
        'pytest.case:detail': '允许查看 pytest 用例文件和执行结果。',
        'pytest.case:execute': '允许执行 pytest 用例。',
        'pytest.case:publish': '允许提交 Pytest 用例预发布，由产品负责人通过发布或退回。',
        'data_factory.entity:create': '允许新增实体、批量生成实体或生成字段配置。',
        'data_factory.entity:detail': '允许查看实体字段和结构详情。',
        'data_factory.entity:debug': '允许加载表、预览字段实际值或测试数据发现能力。',
        'data_factory.entity:status': '允许启用或停用数据实体。',
        'data_factory.template:detail': '允许查看场景模板配置和预览数据。',
        'data_factory.template:debug': '允许调试运行场景模板和预览生成结果。',
        'data_factory.template:copy': '允许复制场景模板。',
        'data_factory.template:status': '允许启用或停用场景模板。',
        'data_factory.execution:detail': '允许查看数据工厂执行记录、上下文和明细。',
        'report:detail': '允许查看测试报告明细、汇总、执行链路和用例详情。',
        'report:retry': '允许重试、停止测试报告或重试失败用例。',
        'report:notice': '允许发送测试报告通知。',
        'report:download': '允许下载测试报告导出文件。',
        'report:export': '允许导出测试报告明细。',
        'timing.tasks:execute': '允许手动触发定时任务执行。',
        'timing.tasks:status': '允许启用、停用或切换定时任务状态。',
        'timing.system_jobs:execute': '允许触发系统内置任务执行。',
        'config.project:detail': '允许查看项目通知组和项目关联配置。',
        'config.project:debug': '允许测试项目通知组配置。',
        'config.product:detail': '允许查看项目产品模块名称等配置。',
        'config.product:query': '允许在逻辑数据库中执行 SQL 查询。',
        'config.product:status': '允许启用或停用项目产品相关配置。',
        'config.datasource:detail': '允许查看全局数据库配置。',
        'config.datasource:debug': '允许测试全局数据库配置。',
        'config.test_object:status': '允许启用或停用测试对象配置。',
        'config.test_files:download': '允许获取测试文件下载地址并下载文件。',
        'system.settings:detail': '允许查看系统配置详情。',
        'system.runtime_center:detail': '允许查看服务状态、队列和诊断信息。',
        'system.error_record:detail': '允许查看系统异常详情和关联日志。',
        'pytest.repository:execute': '允许拉取和推送仓库代码。',
        'report.effectiveness:debug': '允许生成 AI 质量分析和清理质量效能缓存。',
        'system.settings:debug': '允许测试系统配置、刷新方法缓存或切换调试日志。',
        'system.execution_result:delete': '允许手动清理超过保留天数的执行结果完整数据或结果文件，执行记录本身会保留。',
        'system.role:detail': '允许查看角色权限树和角色权限详情。',
        'system.department:detail': '允许查看部门项目产品范围。',
        'ai.skill:detail': '允许查看 AI Skill 文件和配置详情。',
        'ai.skill:download': '允许下载 AI Skill 文件。',
        'ai.skill:status': '允许发布、停用或归档 AI Skill。',
        'ai.mcp:detail': '允许查看 MCP 服务工具列表和服务详情。',
        'ai.mcp:debug': '允许测试 MCP 服务或调用 MCP 工具。',
        'ai.mcp:status': '允许刷新 MCP 状态、同步内置服务和同步工具。',
        'ai.task:detail': '允许查看 AI 任务、步骤和工具调用详情。',
        'ai.task:debug': '允许确认 AI 工具调用等调试动作。',
        'ai.task:retry': '允许重试 AI 执行任务。',
        'monitoring.task:detail': '允许查看脚本运行器日志、文件和详情。',
        'monitoring.task:execute': '允许启动或停止脚本运行任务。',
        'monitoring.task:download': '允许下载脚本运行日志。',
        'monitoring.report:detail': '允许查看预警监控报告详情。',
        'equipment.actuator:detail': '允许查看执行器在线状态、配置和用户连接信息。',
        'equipment.actuator:debug': '允许调试执行器或打开浏览器对象。',
        'equipment.actuator:status': '允许切换执行器打开状态。',
        'gray.repository:debug': '允许测试灰度 Git 连接。',
        'gray.repository:execute': '允许同步灰度仓库。',
        'gray.config_file:detail': '允许查看灰度配置文件内容和仓库文件列表。',
        'gray.feature:debug': '允许预览灰度变更。',
        'gray.feature:execute': '允许手动执行灰度变更。',
        'gray.execution_log:detail': '允许查看灰度执行详情。',
        'gray.execution_log:execute': '允许重试灰度恢复。',
        'functional.suite:create': '允许新增需求和需求资料。',
        'functional.suite:detail': '允许查看需求用例、原文资料和需求详情。',
        'functional.iteration:create': '允许创建 Sprint。',
        'functional.iteration:edit': '允许编辑 Sprint 和需求排期。',
        'functional.iteration:delete': '允许删除没有需求和测试计划的 Sprint。',
        'functional.iteration:detail': '允许查看 Sprint 详情、排期表和用户甘特图。',
        'functional.case:create': '允许新增、自动生成或批量生成测试用例。',
        'functional.case:detail': '允许查看测试用例详情和自动化绑定信息。',
        'functional.case:export': '允许导出功能测试用例。',
        'api.module_coverage:create': '允许创建模块扫描并上传扫描 Case。',
        'api.module_coverage:edit': '允许完成扫描和绑定 ApiCase。',
        'api.module_coverage:delete': '允许归档代码扫描覆盖 Case。',
        'api.module_coverage:detail': '允许查看扫描详情、Case 场景、调用流程和覆盖证据。',
        'functional.plan:create': '允许创建测试计划并从用例库选择用例。',
        'functional.plan:edit': '允许编辑计划、调整计划快照和增删计划用例。',
        'functional.plan:detail': '允许查看测试计划、计划用例和执行结果。',
        'functional.plan:execute': '允许开始、填写结果和完成测试计划。',
        'functional.defect:create': '允许创建缺陷并关联用例或计划用例。',
        'functional.defect:edit': '允许编辑缺陷内容和关联关系。',
        'functional.defect:delete': '允许删除缺陷。',
        'functional.defect:detail': '允许查看缺陷详情和关联执行现场。',
        'functional.defect:status': '允许流转缺陷状态。',
        'perf.scenario:detail': '允许查看性能场景配置和校验结果。',
        'perf.scenario:execute': '允许执行性能场景。',
        'perf.run:detail': '允许查看性能运行实时指标、报告和快照。',
        'perf.run:stop': '允许停止或取消性能运行。',
        'perf.run:execute': '允许重新汇总性能运行结果。',
        'perf.run:baseline': '允许设置性能基线。',
        'evaluation.dataset:publish': '允许发布不可变评测数据集版本。',
        'evaluation.case:execute': '允许执行评测 Case 和重试失败数据。',
        'evaluation.case:stop': '允许停止当前 Case 的执行。',
        'evaluation.dataset:import': '允许从有权查看的 API 用例导入当前草稿数据。',
        'help.variable:debug': '允许测试随机数据方法。',
        'help.assertion:debug': '允许测试用例断言方法。',
    }

    DEFAULT_ACTIONS = ()
    MENU_ACTIONS = {
        'api.info': ('create', 'edit', 'delete', 'detail', 'debug', 'execute', 'download', 'publish', 'status'),
        'api.case': ('create', 'edit', 'delete', 'detail', 'debug', 'execute', 'copy', 'publish', 'status'),
        'api.public': ('create', 'edit', 'delete', 'status'),
        'api.auth_config': ('create', 'edit', 'delete', 'detail', 'debug', 'status'),
        'api.headers': ('create', 'edit', 'delete', 'status'),
        'api.mock': ('create', 'edit', 'delete', 'detail', 'debug', 'status', 'export'),
        'ui.page': ('create', 'edit', 'delete', 'detail', 'debug', 'download'),
        'ui.page_steps': ('create', 'edit', 'delete', 'detail', 'debug', 'copy'),
        'ui.case': ('create', 'edit', 'delete', 'detail', 'execute', 'debug', 'copy', 'publish'),
        'ui.public': ('create', 'edit', 'delete', 'status'),
        'ui.auth_config': ('create', 'edit', 'delete', 'detail', 'debug', 'status'),
        'pytest.repository': ('create', 'edit', 'delete', 'detail', 'debug', 'execute'),
        'pytest.product': ('create', 'edit', 'delete', 'detail'),
        'pytest.case': ('edit', 'delete', 'detail', 'execute', 'publish'),
        'data_factory.entity': ('create', 'edit', 'delete', 'detail', 'debug', 'status'),
        'data_factory.template': ('create', 'edit', 'delete', 'detail', 'debug', 'copy', 'status'),
        'data_factory.execution': ('detail', 'delete'),
        'gray.repository': ('create', 'edit', 'delete', 'debug', 'execute', 'status'),
        'gray.config_file': ('create', 'edit', 'delete', 'detail', 'status'),
        'gray.feature': ('create', 'edit', 'delete', 'debug', 'execute', 'status'),
        'gray.execution_log': ('detail', 'delete', 'execute'),
        'report': ('detail', 'retry', 'notice', 'download', 'export', 'exclude'),
        'report.effectiveness': ('debug', 'export'),
        'timing.tasks': ('create', 'edit', 'delete', 'execute', 'status'),
        'timing.strategy': ('create', 'edit', 'delete'),
        'timing.fire_record': (),
        'timing.system_jobs': ('execute',),
        'config.project': ('create', 'edit', 'delete', 'detail', 'debug', 'status'),
        'config.product': ('create', 'edit', 'delete', 'detail', 'query', 'status'),
        'config.datasource': ('create', 'edit', 'delete', 'detail', 'debug'),
        'config.test_object': ('create', 'edit', 'delete', 'status'),
        'config.test_files': ('create', 'edit', 'delete', 'download'),
        'system.settings': ('edit', 'debug', 'detail'),
        'system.runtime_center': ('detail',),
        'system.error_record': ('detail',),
        'system.execution_result': ('delete',),
        'system.user': ('create', 'edit', 'delete'),
        'system.role': ('create', 'edit', 'delete', 'detail'),
        'system.department': ('create', 'edit', 'delete', 'detail'),
        'system.user_logs': (),
        'ai.skill': ('create', 'edit', 'delete', 'detail', 'download', 'status'),
        'ai.mcp': ('create', 'edit', 'delete', 'detail', 'debug', 'status'),
        'ai.task': ('create', 'delete', 'detail', 'debug', 'retry', 'execute'),
        'monitoring.task': ('create', 'edit', 'delete', 'execute', 'detail', 'download'),
        'monitoring.report': ('detail',),
        'equipment.actuator': ('detail', 'debug', 'edit', 'status'),
        'functional.suite': ('create', 'edit', 'delete', 'detail'),
        'functional.iteration': ('create', 'edit', 'delete', 'detail'),
        'functional.case': ('create', 'edit', 'delete', 'detail', 'export'),
        'api.module_coverage': ('create', 'edit', 'delete', 'detail'),
        'functional.plan': ('create', 'edit', 'delete', 'detail', 'copy', 'execute'),
        'functional.defect': ('create', 'edit', 'delete', 'detail', 'status'),
        'perf.scenario': ('create', 'edit', 'delete', 'detail', 'execute'),
        'perf.run': ('detail', 'stop', 'execute', 'baseline', 'export', 'download'),
        'perf.capacity': (),
        'evaluation.dataset': ('create', 'edit', 'delete', 'detail', 'publish', 'import', 'status'),
        'evaluation.case': ('create', 'edit', 'delete', 'detail', 'status', 'execute', 'stop', 'copy'),
        'evaluation.grader': ('detail',),
        'help.variable': ('debug',),
        'help.assertion': ('debug',),
    }

    @classmethod
    def is_effective_super_admin(cls, user: User) -> bool:
        if user.is_super_admin:
            return True
        if user.username == 'admin' and not User.objects.filter(is_super_admin=True).exists():
            user.is_super_admin = True
            user.save(update_fields=['is_super_admin', 'update_time'])
            return True
        return False

    @classmethod
    def ensure_guest_role(cls) -> Role:
        role, _ = Role.objects.get_or_create(
            name=GUEST_ROLE_NAME,
            defaults={'description': '新用户默认角色，可查看非系统管理页面，禁止新增、编辑、删除'}
        )
        permissions = cls.guest_permission_keys()
        current_permissions = set(
            RoleMenuPermission.objects.filter(role=role).values_list('permission_key', flat=True)
        )
        if current_permissions != permissions:
            RoleMenuPermission.objects.filter(role=role).delete()
            RoleMenuPermission.objects.bulk_create([
                RoleMenuPermission(
                    role=role,
                    permission_key=permission_key,
                    permission_type='action' if ':' in permission_key else 'page'
                )
                for permission_key in sorted(permissions)
            ])
        return role

    @classmethod
    def default_role(cls) -> Role:
        return cls.ensure_guest_role()

    @classmethod
    def permission_keys_for_user(cls, user: User) -> set[str]:
        if cls.is_effective_super_admin(user):
            return cls.all_permission_keys()
        if not user.role_id:
            return cls.guest_permission_keys()
        if user.role and user.role.name == GUEST_ROLE_NAME:
            cls.ensure_guest_role()
        keys = cls.normalize_legacy_permission_keys(
            RoleMenuPermission.objects.filter(role_id=user.role_id)
            .values_list('permission_key', flat=True)
        )
        keys &= cls.all_permission_keys()
        keys.add(HOME_PERMISSION_KEY)
        return keys

    @classmethod
    def all_permission_keys(cls) -> set[str]:
        keys = set()
        for item in cls.permission_tree():
            cls._collect_permission_keys(item, keys)
        return keys

    @classmethod
    def guest_permission_keys(cls) -> set[str]:
        keys = set()
        for item in cls.permission_tree():
            cls._collect_guest_permission_keys(item, keys)
        keys.add(HOME_PERMISSION_KEY)
        return keys

    @classmethod
    def role_permission_keys(cls, role_id: int) -> set[str]:
        keys = cls.normalize_legacy_permission_keys(
            RoleMenuPermission.objects.filter(role_id=role_id)
            .values_list('permission_key', flat=True)
        )
        keys &= cls.all_permission_keys()
        keys.add(HOME_PERMISSION_KEY)
        return keys

    @classmethod
    @transaction.atomic
    def save_role_permissions(cls, role_id: int, permission_keys: Iterable[str], update_user_id: int | None = None):
        valid_keys = cls.all_permission_keys()
        selected_keys = cls.normalize_legacy_permission_keys(permission_keys) & valid_keys
        selected_keys.add(HOME_PERMISSION_KEY)
        RoleMenuPermission.objects.filter(role_id=role_id).delete()
        RoleMenuPermission.objects.bulk_create([
            RoleMenuPermission(
                role_id=role_id,
                permission_key=key,
                permission_type='action' if ':' in key else 'page',
                update_user_id=update_user_id,
            )
            for key in sorted(selected_keys)
        ])
        return selected_keys

    @staticmethod
    def normalize_legacy_permission_keys(permission_keys: Iterable[str]) -> set[str]:
        return {
            key.replace('config.data_source', 'config.datasource', 1)
            if key == 'config.data_source' or key.startswith('config.data_source:') else key
            for key in permission_keys
        }

    @classmethod
    def permitted_menu(cls, user: User) -> dict:
        keys = cls.permission_keys_for_user(user)
        routes = cls.filter_routes_by_permissions(ad_routes(), keys)
        return {
            'menus': routes,
            'permissions': sorted(keys),
            'is_super_admin': cls.is_effective_super_admin(user),
        }

    @classmethod
    def permission_tree(cls) -> list[dict]:
        routes = deepcopy(ad_routes())
        for item in routes:
            cls._decorate_menu_item(item)
        return routes

    @classmethod
    def filter_routes_by_permissions(cls, routes: list[dict], keys: set[str]) -> list[dict]:
        result = []
        for item in deepcopy(routes):
            cls._decorate_menu_item(item)
            children = item.get('children') or []
            if children:
                filtered_children = cls.filter_routes_by_permissions(children, keys)
                if filtered_children:
                    item['children'] = filtered_children
                    result.append(item)
                continue
            if item.get('permissionKey') in keys:
                result.append(item)
        return result

    @classmethod
    def _decorate_menu_item(cls, item: dict):
        item.setdefault('isBeta', False)
        key = item.get('permissionKey') or item.get('menuKey') or cls.menu_key_from_url(item.get('menuUrl'))
        if key:
            item['permissionKey'] = key
        children = item.get('children') or []
        for child in children:
            cls._decorate_menu_item(child)
        if children and key and any(child.get('permissionKey') == key for child in children):
            item['permissionKey'] = f'{key}.__group'
        if not children and key:
            item.setdefault('actions', cls.default_actions_for_menu(key))
            item['statusFields'] = list(STATUS_PERMISSION_FIELDS.get(key, ()))

    @staticmethod
    def status_fields_for_model(page_key, model, data):
        configured = STATUS_PERMISSION_FIELDS.get(page_key, ())
        if not configured or model is None or not isinstance(data, dict):
            return set()
        fields = {field.name for field in model._meta.fields}
        return set(configured) & fields & data.keys()

    @staticmethod
    def payload_changes_status(page_key, data):
        return any(data.get(field) is not None for field in STATUS_PERMISSION_FIELDS.get(page_key, ()))

    @classmethod
    def default_actions_for_menu(cls, menu_key: str) -> list[dict]:
        action_keys = tuple(dict.fromkeys((*cls.DEFAULT_ACTIONS, *cls.MENU_ACTIONS.get(menu_key, ()))))
        return [
            {
                'permissionKey': f'{menu_key}:{action}',
                'permissionName': cls.ACTION_LABELS[action],
                'permissionDescription': cls.action_description(menu_key, action),
                'permissionType': 'action',
            }
            for action in action_keys
        ]

    @classmethod
    def action_description(cls, menu_key: str, action: str) -> str:
        return cls.ACTION_DESCRIPTION_OVERRIDES.get(
            f'{menu_key}:{action}',
            cls.ACTION_DESCRIPTIONS[action]
        )

    @classmethod
    def menu_key_from_url(cls, url: str | None) -> str | None:
        if not url or url.startswith('http'):
            return None
        parts = [part for part in url.strip('/').split('/') if part and part != 'index']
        if not parts:
            return None
        if url.strip('/') == 'index/home':
            return HOME_PERMISSION_KEY
        root_alias = {
            'apitest': 'api',
            'uitest': 'ui',
            'functional-test': 'functional',
            'data-factory': 'data_factory',
        }
        parts[0] = root_alias.get(parts[0], parts[0].replace('-', '_'))
        return '.'.join(part.replace('-', '_') for part in parts)

    @classmethod
    def _collect_permission_keys(cls, item: dict, keys: set[str]):
        key = item.get('permissionKey')
        if key:
            keys.add(key)
        for action in item.get('actions') or []:
            action_key = action.get('permissionKey')
            if action_key:
                keys.add(action_key)
        for child in item.get('children') or []:
            cls._collect_permission_keys(child, keys)

    @classmethod
    def _collect_guest_permission_keys(cls, item: dict, keys: set[str]):
        key = item.get('permissionKey')
        page_allowed = bool(key) and cls._is_guest_allowed_page_key(key)
        if page_allowed:
            keys.add(key)
            for action in item.get('actions') or []:
                action_key = action.get('permissionKey')
                if action_key and cls._is_guest_allowed_action_key(action_key):
                    keys.add(action_key)
        for child in item.get('children') or []:
            cls._collect_guest_permission_keys(child, keys)

    @staticmethod
    def _is_guest_allowed_page_key(key: str) -> bool:
        if key in GUEST_DENIED_PAGE_KEYS:
            return False
        return not key.startswith(GUEST_DENIED_PAGE_PREFIXES)

    @classmethod
    def _is_guest_allowed_action_key(cls, key: str) -> bool:
        if ':' not in key or key in GUEST_DENIED_ACTION_KEYS:
            return False
        page_key, action = key.split(':', 1)
        return cls._is_guest_allowed_page_key(page_key) and action in GUEST_ALLOWED_ACTIONS


class ProjectProductScopeService:
    @staticmethod
    def strict_project_product_ids_for_user(user: User) -> set[int]:
        """风险数据只按真实部门授权范围返回，不应用访客全量查看开关。"""
        department_ids = UserDepartment.objects.filter(user=user).values_list('department_id', flat=True)
        return set(
            DepartmentProjectProductPermission.objects.filter(department_id__in=department_ids)
            .values_list('project_product_id', flat=True)
        )

    @classmethod
    def project_product_ids_for_user(cls, user: User) -> set[int]:
        if PermissionMenuService.is_effective_super_admin(user) or cls.can_view_all_project_data(user):
            return set()
        department_ids = UserDepartment.objects.filter(user=user).values_list('department_id', flat=True)
        return set(
            DepartmentProjectProductPermission.objects.filter(department_id__in=department_ids)
            .values_list('project_product_id', flat=True)
        )

    @classmethod
    def has_project_product(cls, user: User, project_product_id: int | None) -> bool:
        if PermissionMenuService.is_effective_super_admin(user) or cls.can_view_all_project_data(
                user) or project_product_id is None:
            return True
        allowed_ids = cls.project_product_ids_for_user(user)
        return project_product_id in allowed_ids

    @classmethod
    def can_view_all_project_data(cls, user: User) -> bool:
        from src.apps.system.services.system_config import SystemConfigService

        role = getattr(user, 'role', None)
        is_guest = not getattr(user, 'role_id', None) or (
                role is not None and role.name == GUEST_ROLE_NAME
        )
        return is_guest and SystemConfigService.guest_can_view_all_project_data()
