from functools import lru_cache
import re

from django.urls import URLResolver, get_resolver

from src.apps.user.services.http_permission_registry import HTTP_PERMISSION_RULES
from src.apps.user.services.http_permission_boundaries import HTTP_PERMISSION_BOUNDARIES


REPOSITORY_UPSERT_VIEW = 'src.apps.auto_pytest.api.views.pytest_repository.PytestRepositoryViews'


@lru_cache(maxsize=1)
def http_permission_catalog() -> tuple[dict, ...]:
    """公开前端请求分类元数据，不包含角色授权或业务数据。"""
    result = []

    def walk(patterns, prefix=''):
        for pattern in patterns:
            expression = prefix + pattern.pattern.regex.pattern.removeprefix('^').removesuffix('\\Z').removesuffix('$')
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns, expression)
                continue
            view = getattr(pattern.callback, 'cls', None) or getattr(pattern.callback, 'view_class', None)
            if view is None:
                continue
            view_key = f'{view.__module__}.{view.__name__}'
            methods = getattr(pattern.callback, 'actions', None) or {
                method: method for method in getattr(view, 'http_method_names', ())
                if method not in {'head', 'options'} and hasattr(view, method)
            }
            for method, action in methods.items():
                if (view_key, action, method) in HTTP_PERMISSION_BOUNDARIES:
                    continue
                required = HTTP_PERMISSION_RULES.get((view_key, action, method))
                if not required:
                    continue
                keys = [required] if isinstance(required, str) else list(required)
                item = {
                    'pattern': '^/' + re.sub(r'\(\?P<[^>]+>', '(?:', expression).removeprefix('api/').removeprefix('/') + '$',
                    'method': method.upper(),
                    'permissions': keys,
                }
                if view_key == REPOSITORY_UPSERT_VIEW and action == 'save_repository':
                    item['updatePermissions'] = ['pytest.repository:change']
                result.append(item)

    walk(get_resolver().url_patterns)
    return tuple(result)
