from src.common.enums.base import BaseEnum


class PytestRepositoryProviderEnum(BaseEnum):
    GITLAB = ('gitlab', 'GitLab')
    GITHUB = ('github', 'GitHub')
    GITEE = ('gitee', 'Gitee')


class PytestRepositorySyncStatusEnum(BaseEnum):
    IDLE = (0, '空闲')
    SYNCING = (1, '同步中')
    SUCCESS = (2, '同步成功')
    FAILED = (3, '同步失败')


class PytestRepositoryCredentialTypeEnum(BaseEnum):
    TOKEN = ('token', 'Token')
    USERNAME_PASSWORD = ('username_password', '用户名密码')
