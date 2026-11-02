from django.db.models import TextChoices


class PageOperationEnum(TextChoices):
    READ = 'read', '查看'
    ADD = 'add', '新增'
    CHANGE = 'change', '修改'
    REMOVE = 'remove', '删除'


class HttpPermissionBoundaryEnum(TextChoices):
    PUBLIC = 'public', '公开登录与下载'
    BOOTSTRAP = 'bootstrap', '登录用户权限初始化'
    ACCOUNT = 'account', '当前用户个人设置'
    SHARED_REPORT = 'shared_report', '分享凭据只读报告'
    ACTUATOR = 'actuator', '执行器身份协议'
    PERF_NODE = 'perf_node', '性能执行节点协议'
    MOCK_RUNTIME = 'mock_runtime', 'Mock 运行时协议'
    DISABLED = 'disabled', '未开放接口'
