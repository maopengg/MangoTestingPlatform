from rest_framework.permissions import BasePermission

from src.apps.user.services.permission import PermissionMenuService


class MenuActionPermission(BasePermission):
    MUTATION_METHODS = {'post', 'put', 'patch', 'delete'}
    PUBLIC_CACHE_DATA_KEYS = {
        'test_data_select_value',
        'ass_select_value',
        'select_value',
    }
    PUBLIC_PATH_PREFIXES = (
        '/api/login',
        '/api/cli/auth/token',
        '/api/cli/auth/version',
        '/api/register',
        '/api/user/registration-config',
        '/api/reset-password',
        '/api/menu',
        '/api/download',
        '/api/docs',
        '/management/health',
        '/api/system/test/suite/share',
        '/api/system/test/suite/details/share',
        '/api/system/test/suite/details/result/share',
        '/api/system/test/suite/details/summary/share',
        '/api/system/test/suite/details/api/export',
        '/api/system/test/suite/details/api/export/status',
        '/api/system/test/suite/details/api/export/download',
    )
    OPTION_PATH_SUFFIXES = (
        '/name',
        '/all',
        '/all/module/name',
        '/type/case/name',
        '/project/product/name',
        '/project/environment/name',
        '/project/pytest/name',
        '/module/name',
    )
    PATH_PERMISSION_PREFIXES = (
        ('/api/api/mock/', 'api.mock'),
        ('/api/api/case/data-factory', 'api.case'),
        ('/api/api/case/detailed/parameter', 'api.case'),
        ('/api/api/case/detailed', 'api.case'),
        ('/api/api/auth/config', 'api.auth_config'),
        ('/api/api/info', 'api.info'),
        ('/api/api/case', 'api.case'),
        ('/api/api/public', 'api.public'),
        ('/api/api/headers', 'api.headers'),
        ('/api/ui/page/steps/detailed', 'ui.page_steps'),
        ('/api/ui/page/steps', 'ui.page_steps'),
        ('/api/ui/case/steps/detailed', 'ui.case'),
        ('/api/ui/auth/config', 'ui.auth_config'),
        ('/api/ui/page', 'ui.page'),
        ('/api/ui/element', 'ui.page'),
        ('/api/ui/case', 'ui.case'),
        ('/api/ui/public', 'ui.public'),
        ('/api/pytest/product', 'pytest.product'),
        ('/api/pytest/case', 'pytest.case'),
        ('/api/data-factory/datasource-alias', 'config.product'),
        ('/api/data-factory/datasource-binding', 'config.product'),
        ('/api/data-factory/entity', 'data_factory.entity'),
        ('/api/data-factory/field', 'data_factory.entity'),
        ('/api/data-factory/template', 'data_factory.template'),
        ('/api/data-factory/case-config', 'data_factory.template'),
        ('/api/data-factory/execution/item', 'data_factory.execution'),
        ('/api/data-factory/execution', 'data_factory.execution'),
        ('/api/functional-test/suite', 'functional.suite'),
        ('/api/functional-test/plan', 'functional.plan'),
        ('/api/functional-test/grid-view', 'functional.case'),
        ('/api/functional-test/case/automation', 'functional.case'),
        ('/api/functional-test/case', 'functional.case'),
        ('/api/functional-test/context-resource', 'functional.suite'),
        ('/api/evaluation/dataset', 'evaluation.dataset'),
        ('/api/evaluation/case', 'evaluation.case'),
        ('/api/evaluation/graders', 'evaluation.grader'),
        ('/api/monitoring/task', 'monitoring.task'),
        ('/api/monitoring/report', 'monitoring.report'),
        ('/api/system/test/suite/details', 'report'),
        ('/api/system/test/suite', 'report'),
        ('/api/system/tasks/fire-record', 'timing.fire_record'),
        ('/api/system/tasks/system/jobs', 'timing.system_jobs'),
        ('/api/system/tasks/details', 'timing.tasks'),
        ('/api/system/tasks', 'timing.tasks'),
        ('/api/system/time', 'timing.strategy'),
        ('/api/system/file', 'config.test_files'),
        ('/api/system/data-source', 'config.datasource'),
        ('/api/system/database', 'config.datasource'),
        ('/api/system/test/object', 'config.test_object'),
        ('/api/system/project', 'config.project'),
        ('/api/system/product', 'config.product'),
        ('/api/system/module', 'config.product'),
        ('/api/system/notice', 'config.project'),
        ('/api/system/cache/data', 'system.settings'),
        ('/api/system/ai/test', 'system.settings'),
        ('/api/system/set/debug/log', 'system.settings'),
        ('/api/system/runtime', 'system.settings'),
        ('/api/system/sql-execution', 'system.sql_execution'),
        ('/api/ai/skill', 'ai.skill'),
        ('/api/ai/mcp/server', 'ai.mcp'),
        ('/api/ai/mcp/tool', 'ai.mcp'),
        ('/api/ai/task', 'ai.task'),
        ('/api/ai/agent', 'ai.task'),
    )

    def has_permission(self, request, view):
        if (
                request.path in self.PUBLIC_PATH_PREFIXES
                or request.path.startswith('/api/docs')
                or request.path.startswith('/api/actuator/tasks/')
                or request.path.startswith('/api/perf/run-node/')
        ):
            return True
        user_context = getattr(request, 'user', None)
        user = getattr(user_context, 'user_obj', None)
        if user is None:
            return True
        if PermissionMenuService.is_effective_super_admin(user):
            return True
        if self._is_own_user_info_request(request, user):
            return 'index.home' in PermissionMenuService.permission_keys_for_user(user)
        if self._is_option_request(request):
            return True
        if self._is_public_cache_data_key_value_request(request):
            return True
        permission_key = self._resolve_permission_key(request, view)
        if not permission_key:
            return request.method.lower() not in self.MUTATION_METHODS
        allowed_keys = PermissionMenuService.permission_keys_for_user(user)
        status_fields = self._status_fields(request, view)
        if status_fields and f'{view.page_permission_key}:status' not in allowed_keys:
            return False
        if isinstance(permission_key, (tuple, list, set)):
            return any(key in allowed_keys for key in permission_key)
        return permission_key in allowed_keys

    @staticmethod
    def _status_fields(request, view):
        if request.method.lower() not in ('put', 'patch'):
            return set()
        return PermissionMenuService.status_fields_for_model(
            getattr(view, 'page_permission_key', None), getattr(view, 'model', None), request.data,
        )

    @staticmethod
    def _is_own_user_info_request(request, user):
        if request.method.lower() != 'get' or request.path != '/api/user/info':
            return False
        try:
            return int(request.query_params.get('id')) == user.id
        except (TypeError, ValueError):
            return False

    @classmethod
    def _is_option_request(cls, request):
        return request.method.lower() == 'get' and request.path.endswith(cls.OPTION_PATH_SUFFIXES)

    @classmethod
    def _is_public_cache_data_key_value_request(cls, request):
        if request.method.lower() != 'get' or request.path != '/api/system/cache/data/key/value':
            return False
        raw_keys = request.query_params.getlist('keys[]') or request.query_params.getlist('keys')
        keys = [
            key.strip()
            for item in raw_keys
            for key in str(item).split(',')
            if key.strip()
        ]
        if not keys:
            key = request.query_params.get('key')
            keys = [str(key).strip()] if key else []
        return bool(keys) and all(key in cls.PUBLIC_CACHE_DATA_KEYS for key in keys)

    @classmethod
    def _resolve_permission_key(cls, request, view):
        action_map = getattr(view, 'action_permission_map', None) or {}
        action = getattr(view, 'action', None)
        if action and action in action_map:
            return action_map[action]
        if hasattr(view, 'get_permission_key_map'):
            method_map = view.get_permission_key_map()
        else:
            method_map = getattr(view, 'permission_key_map', None) or {}
        permission_key = method_map.get(request.method.lower())
        status_fields = cls._status_fields(request, view)
        if status_fields and set(request.data) <= status_fields | {'id', 'update_time'}:
            return f'{view.page_permission_key}:status'
        if permission_key:
            return permission_key
        return cls._resolve_permission_key_by_path(request)

    @classmethod
    def _resolve_permission_key_by_path(cls, request):
        path = request.path
        if request.method.lower() == 'get' and path.endswith(cls.OPTION_PATH_SUFFIXES):
            return None
        for prefix, page_key in cls.PATH_PERMISSION_PREFIXES:
            if not path.startswith(prefix):
                continue
            action = cls._action_from_path_and_method(path, request.method.lower())
            return f'{page_key}:{action}' if action else page_key
        return None

    @classmethod
    def _action_from_path_and_method(cls, path: str, method: str):
        if method == 'get':
            if any(token in path for token in ('/case/test', '/batch', '/trigger', '/run')):
                return 'execute'
            if any(token in path for token in ('/test', '/debug')):
                return 'debug'
            if any(token in path for token in ('/export',)):
                return 'export'
            if any(token in path for token in ('/download',)):
                return 'download'
            if any(token in path for token in ('/retry',)):
                return 'retry'
            return None
        if method == 'post':
            if any(token in path for token in ('/query',)):
                return 'query'
            if any(token in path for token in ('/batch', '/trigger', '/start', '/run')):
                return 'execute'
            if any(token in path for token in ('/test', '/debug')):
                return 'debug'
            if any(token in path for token in ('/copy',)):
                return 'copy'
            if any(token in path for token in ('/retry',)):
                return 'retry'
            if any(token in path for token in ('/notice',)):
                return 'notice'
            if any(token in path for token in ('/export',)):
                return 'export'
            return 'create'
        if method == 'put':
            if any(token in path for token in ('/status', '/type', '/schema')):
                return 'status'
            return 'edit'
        if method == 'delete':
            return 'delete'
        return None
