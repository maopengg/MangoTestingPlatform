from rest_framework.throttling import ScopedRateThrottle


class MangoScopedRateThrottle(ScopedRateThrottle):
    scope_attr = 'throttle_scope'


class LoginThrottle(MangoScopedRateThrottle):
    scope = 'login'


class AiThrottle(MangoScopedRateThrottle):
    scope = 'ai'


class ExecuteThrottle(MangoScopedRateThrottle):
    scope = 'execute'


class ExportThrottle(MangoScopedRateThrottle):
    scope = 'export'


class DownloadThrottle(MangoScopedRateThrottle):
    scope = 'download'
