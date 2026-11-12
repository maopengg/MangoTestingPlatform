"""接口身份取自显式注册表；URL 和注释只用于展示，不参与权限推断。"""
import ast
import hashlib
import inspect
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.urls import URLResolver, get_resolver

from src.apps.user.enums.permission import FixedEndpointCategoryEnum, HttpPermissionBoundaryEnum

from src.apps.user.services.authorization.http_permission_boundaries import HTTP_FIXED_BUSINESS_ENDPOINTS, HTTP_PERMISSION_BOUNDARIES
from src.apps.user.services.authorization.http_permission_registry import HTTP_PERMISSION_RULES
from src.apps.user.services.authorization.mcp_permission_registry import MCP_PERMISSION_RULES
from src.apps.user.services.authorization.permission import PermissionMenuService


def http_endpoint_id(owner, action, method, branch=None):
    value = '\n'.join((owner, action, method.lower(), *([branch] if branch else [])))
    return 'http.' + hashlib.sha256(value.encode()).hexdigest()


def http_request_endpoint_id(owner, action, method, required):
    if (owner, action) == ('src.apps.auto_pytest.api.views.pytest_repository.PytestRepositoryViews', 'save_repository'):
        return http_endpoint_id(owner, action, method, required)
    return http_endpoint_id(owner, action, method)


def mcp_endpoint_id(name):
    return 'mcp.' + hashlib.sha256(name.encode()).hexdigest()


def permission_keys(required):
    return list(dict.fromkeys([required] if isinstance(required, str) else required or ()))


def fixed_business_rule(required):
    keys = permission_keys(required)
    return any(PermissionMenuService.is_default_read_key(key) for key in keys)


def _function_description(documentation):
    lines = []
    for line in (documentation or '').strip().splitlines():
        line = line.strip()
        if not line or line.startswith(('@param', '@return', ':param', ':return', 'Args:', 'Returns:')):
            break
        lines.append(line)
    return ' '.join(lines)[:600]


@lru_cache(maxsize=1)
def endpoint_catalog():
    rows = {}
    model_menus = {}
    endpoint_tables = {}
    valid_menus = {key for key in PermissionMenuService.all_permission_keys() if ':' not in key}

    def walk(patterns, prefix=''):
        for pattern in patterns:
            url = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, url)
                continue
            view = getattr(pattern.callback, 'cls', None) or getattr(pattern.callback, 'view_class', None)
            if view is None:
                continue
            owner = f'{view.__module__}.{view.__name__}'
            methods = getattr(pattern.callback, 'actions', None) or {
                method: method for method in getattr(view, 'http_method_names', ())
                if method not in {'head', 'options'} and hasattr(view, method)
            }
            for method, action in methods.items():
                key = (owner, action, method.lower())
                boundary = HTTP_PERMISSION_BOUNDARIES.get(key)
                required = HTTP_PERMISSION_RULES.get(key)
                if boundary is None and not required:
                    continue
                model = getattr(view, 'model', None)
                table = getattr(getattr(model, '_meta', None), 'db_table', None)
                if table:
                    declared = getattr(view, 'page_permission_key', None)
                    if declared in valid_menus:
                        model_menus.setdefault(table, set()).add(declared)
                    elif any(base.__module__ == 'src.common.responses.model_crud' for base in view.__mro__):
                        owners = {key.rsplit(':', 1)[0] for key in permission_keys(required)} & valid_menus
                        if len(owners) == 1:
                            model_menus.setdefault(table, set()).update(owners)
                branches = [None]
                if (owner, action) == ('src.apps.auto_pytest.api.views.pytest_repository.PytestRepositoryViews', 'save_repository'):
                    branches = ['pytest.repository:add', 'pytest.repository:change']
                for branch in branches:
                    append_row(view, owner, action, method, url, boundary, required, branch)

    def append_row(view, owner, action, method, url, boundary, required, branch):
        endpoint_id = http_endpoint_id(owner, action, method, branch)
        if endpoint_id in rows:
            rows[endpoint_id]['urls'].append('/' + url.lstrip('/'))
            return
        description = inspect.getdoc(getattr(view, action, None)) or ''
        model = getattr(view, 'model', None)
        endpoint_tables[endpoint_id] = getattr(getattr(model, '_meta', None), 'db_table', None)
        fixed = (boundary is not None or (owner, action, method.lower()) in HTTP_FIXED_BUSINESS_ENDPOINTS
                 or fixed_business_rule(branch or required))
        rows[endpoint_id] = {
            'id': endpoint_id, 'protocol': 'http', 'method': method.upper(),
            'name': action + ({'pytest.repository:add': '（新仓库）', 'pytest.repository:change': '（已有仓库）'}.get(branch, '')),
            'description': _function_description(description),
            'urls': ['/' + url.lstrip('/')], 'permissions': permission_keys(branch or required),
            'fixed': fixed,
            'fixed_enabled': bool(fixed and boundary != HttpPermissionBoundaryEnum.DISABLED),
            'fixed_category': boundary.value if boundary is not None else (
                FixedEndpointCategoryEnum.SHARED_OPTIONS.value
                if (owner, action, method.lower()) in HTTP_FIXED_BUSINESS_ENDPOINTS
                else FixedEndpointCategoryEnum.DEFAULT_READ.value if fixed else None),
            'fixed_reason': boundary.label if boundary is not None else (
                '基础或共用选项，沿用固定授权规则' if fixed else ''),
        }

    walk(get_resolver().url_patterns)
    for endpoint_id, row in rows.items():
        if row['fixed_category'] == FixedEndpointCategoryEnum.DEFAULT_READ.value:
            row['menu_owners'] = list(dict.fromkeys(key.rsplit(':', 1)[0] for key in row['permissions']
                                                   if PermissionMenuService.is_default_read_key(key)))
        else:
            owners = model_menus.get(endpoint_tables.get(endpoint_id), set())
            row['menu_owners'] = sorted(owners) if len(owners) == 1 else []
    metadata = _mcp_component_metadata()
    for name, policy in MCP_PERMISSION_RULES.items():
        required = policy['permission_key']
        fixed = policy['public'] or not required or PermissionMenuService.is_default_read_key(required)
        endpoint_id = mcp_endpoint_id(name)
        rows[endpoint_id] = {
            'id': endpoint_id, 'protocol': 'mcp', 'method': 'MCP', 'name': name,
            'description': metadata.get(name, ''), 'urls': [],
            'permissions': [required] if required else [],
            'additional_permissions': list(policy.get('additional_permission_keys', ())),
            'fixed': bool(fixed), 'fixed_reason': '基础能力或资源入口，沿用固定授权规则' if fixed else '',
            'fixed_enabled': bool(fixed),
            'menu_owners': [required.rsplit(':', 1)[0]] if required and required.rsplit(':', 1)[0] in valid_menus else [],
            'fixed_category': (HttpPermissionBoundaryEnum.PUBLIC.value if policy['public'] else
                               FixedEndpointCategoryEnum.MCP_BASE.value if not required else
                               FixedEndpointCategoryEnum.DEFAULT_READ.value) if fixed else None,
        }
    return tuple(rows.values())


@lru_cache(maxsize=1)
def _mcp_component_metadata():
    # 只读源码取得工具注释，避免导入或初始化 MCP 服务；缺少注释不影响授权。
    root = Path(settings.BASE_DIR) / 'src/interfaces/mcp/tools'
    result = {}
    for path in [*sorted(root.rglob('*.py')), root.parent / 'server.py']:
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (OSError, SyntaxError):
            # 描述不可读取时只展示注册名称，不能改变入口的授权策略。
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                call = decorator.func if isinstance(decorator, ast.Call) else decorator
                if isinstance(call, ast.Attribute) and call.attr in {'tool', 'resource', 'prompt'}:
                    result[node.name] = (ast.get_docstring(node) or '')[:600]
    return result


@lru_cache(maxsize=1)
def configurable_endpoint_ids():
    return frozenset(row['id'] for row in endpoint_catalog() if not row['fixed'])


def grouped_endpoint_catalog():
    groups = {}
    for row in endpoint_catalog():
        if row['fixed'] and row['menu_owners']:
            pages = row['menu_owners']
        elif row['fixed']:
            pages = ['__fixed__', f"__fixed__.{row['fixed_category']}"]
        else:
            pages = list(dict.fromkeys(key.rsplit(':', 1)[0] for key in row['permissions']))
        for page in pages:
            groups.setdefault(page, []).append({key: value for key, value in row.items()
                                               if key not in {'permissions', 'additional_permissions', 'menu_owners'}})
    return [{'menu_key': key, 'endpoints': value} for key, value in groups.items()]


def fixed_endpoint_tree():
    """展示分类不进入路由或角色授权，仅说明系统已有的固定边界。"""
    categories = {row['fixed_category'] for row in endpoint_catalog() if row['fixed'] and not row['menu_owners']}
    return {
        'permissionKey': '__fixed__', 'menuName': '其他', 'displayOnly': True,
        'children': [
            {'permissionKey': f'__fixed__.{item.value}', 'menuName': item.label,
             'displayOnly': True, 'children': []}
            for item in (*HttpPermissionBoundaryEnum, *FixedEndpointCategoryEnum)
            if item.value in categories
        ],
    }
