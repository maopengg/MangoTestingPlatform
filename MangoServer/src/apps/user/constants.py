GUEST_DENIED_ACTION_KEYS = {'ai.task:execute'}

STATUS_PERMISSION_FIELDS = {
    'evaluation.dataset': ('status',),
    'evaluation.case': ('status',),
    'api.headers': ('status',),
    'api.public': ('status',),
    'api.auth_config': ('status',),
    'api.mock': ('enabled', 'record_call_log'),
    'ui.public': ('status',),
    'ui.auth_config': ('status',),
    'data_factory.entity': ('status',),
    'data_factory.template': ('status', 'is_default'),
    'gray.repository': ('status',),
    'gray.config_file': ('status',),
    'gray.feature': ('status',),
    'config.project': ('status',),
    'config.product': ('status', 'db_c_status', 'db_rud_status'),
    'config.test_object': ('status', 'db_c_status', 'db_rud_status'),
    'timing.tasks': ('status', 'is_notice', 'fail_notice'),
    'ai.skill': ('status',),
    'ai.mcp': ('status',),
}
