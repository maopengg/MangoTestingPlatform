from django.db import models

from src.apps.auto_pytest.enums import (
    PytestCasePublicationStatusEnum,
    PytestAssetStatusEnum,
    PytestRepositoryCredentialTypeEnum,
    PytestRepositoryProviderEnum,
    PytestRepositorySyncStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.exceptions import (
    AUTO_PYTEST_GENERAL_TASK_RELATION_DELETE_BINDING_INVALID,
    AutoPytestError,
)
from src.apps.task_center.models import TasksDetails
from src.apps.test_center.models import ProductModule
from src.apps.test_center.models import ProjectProduct
from src.apps.user.models import User


class PytestRepositoryCredential(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    auth_type = models.CharField(
        verbose_name="认证类型",
        max_length=32,
        choices=PytestRepositoryCredentialTypeEnum.choices(),
        default=PytestRepositoryCredentialTypeEnum.TOKEN.value,
    )
    username = models.CharField(verbose_name="用户名", max_length=255, null=True, blank=True)
    secret_ciphertext = models.BinaryField(verbose_name="加密凭证")
    key_version = models.CharField(verbose_name="密钥版本", max_length=32, default="fernet-sha256-v1")
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="pytest_repository_credential_create_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="pytest_repository_credential_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "pytest_repository_credential"
        ordering = ["id"]


class PytestRepository(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="仓库名称", max_length=128)
    provider = models.CharField(
        verbose_name="Git 平台",
        max_length=32,
        choices=PytestRepositoryProviderEnum.choices(),
        default=PytestRepositoryProviderEnum.GITLAB.value,
    )
    # 仓库地址可能超过 MySQL utf8mb4 单列唯一索引的安全长度。
    # 管理入口会先标准化地址并做重复校验，避免为长 URL 建立超长索引。
    repo_url = models.CharField(verbose_name="仓库地址", max_length=1024)
    api_base_url = models.CharField(verbose_name="API 地址", max_length=1024, null=True, blank=True)
    remote_project = models.CharField(verbose_name="远程项目标识", max_length=1024)
    credential = models.OneToOneField(
        to=PytestRepositoryCredential,
        to_field="id",
        related_name="repository",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    default_branch = models.CharField(verbose_name="默认分支", max_length=255, default="master")
    active_branch = models.CharField(verbose_name="当前分支", max_length=255, null=True, blank=True)
    current_commit = models.CharField(verbose_name="当前提交", max_length=128, null=True, blank=True)
    sync_status = models.SmallIntegerField(
        verbose_name="同步状态",
        choices=PytestRepositorySyncStatusEnum.choices(),
        default=PytestRepositorySyncStatusEnum.IDLE.value,
        db_index=True,
    )
    last_sync_time = models.DateTimeField(verbose_name="最近同步时间", null=True, blank=True)
    last_sync_error = models.TextField(verbose_name="最近同步错误", null=True, blank=True)
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="pytest_repository_create_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="pytest_repository_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "pytest_repository"
        ordering = ["name", "id"]


class PytestProduct(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="pytest_product_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="名称", max_length=1024, null=True, blank=True)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024)
    init_file = models.CharField(verbose_name="__init__文件", max_length=1024, null=True, blank=True)
    auto_type = models.SmallIntegerField(verbose_name="自动化类型", default=0)
    test_dir = models.JSONField(verbose_name="测试目录名称", default=list, blank=True)
    repository = models.ForeignKey(
        to=PytestRepository,
        to_field="id",
        related_name="pytest_projects",
        on_delete=models.PROTECT,
    )
    working_directory = models.CharField(verbose_name="执行工作目录", max_length=1024, null=True, blank=True)
    pytest_config_path = models.CharField(verbose_name="Pytest 配置文件", max_length=1024, null=True, blank=True)
    enabled = models.BooleanField(verbose_name="是否启用", default=True, db_index=True)

    class Meta:
        db_table = 'pytest_product'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=PytestProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.SET_NULL, null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.SET_NULL,
                                    null=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="pytest_case_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="自定义用例名称", max_length=1024)
    level = models.SmallIntegerField(verbose_name="用例级别", default=1, db_index=True)
    scenario_layer = models.SmallIntegerField(verbose_name="测试层级", default=0)
    scenario_type = models.SmallIntegerField(verbose_name="验证类型", default=0)
    scenario_tags = models.JSONField(verbose_name="执行场景", default=list, blank=True)
    scenario_description = models.TextField(verbose_name="场景描述", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)
    publication_status = models.CharField(
        verbose_name="发布状态", max_length=32, choices=PytestCasePublicationStatusEnum.choices(),
        default=PytestCasePublicationStatusEnum.UNPUBLISHED.value,
        help_text="用例发布审批状态；仅已发布用例可参与定时执行。",
    )
    file_name = models.CharField(verbose_name="文件名称", max_length=1024)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024)
    feature_file_path = models.CharField(verbose_name="feature文件路径", max_length=1024, null=True, blank=True)
    file_status = models.SmallIntegerField(verbose_name="文件状态", default=0)
    file_update_time = models.DateTimeField(verbose_name="文档修改时间")
    source_status = models.SmallIntegerField(
        verbose_name="源码状态",
        choices=PytestSourceStatusEnum.choices(),
        default=PytestSourceStatusEnum.ACTIVE.value,
        db_index=True,
    )
    asset_status = models.SmallIntegerField(
        verbose_name="资产状态",
        choices=PytestAssetStatusEnum.choices(),
        default=PytestAssetStatusEnum.DRAFT.value,
        db_index=True,
    )
    source_hash = models.CharField(verbose_name="源文件摘要", max_length=64, null=True, blank=True)
    source_commit = models.CharField(verbose_name="同步来源提交", max_length=128, null=True, blank=True)
    first_seen_commit = models.CharField(verbose_name="首次发现提交", max_length=128, null=True, blank=True)
    last_seen_commit = models.CharField(verbose_name="最后发现提交", max_length=128, null=True, blank=True)
    last_seen_time = models.DateTimeField(verbose_name="最后发现时间", null=True, blank=True)
    missing_since = models.DateTimeField(verbose_name="源码缺失时间", null=True, blank=True)
    previous_file_path = models.CharField(verbose_name="历史文件路径", max_length=1024, null=True, blank=True)

    class Meta:
        db_table = 'pytest_case'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['project_product', 'publication_status', '-id'], name='idx_pytest_case_prod_release'),
        ]

    def delete(self, *args, **kwargs):
        if TasksDetails.objects.filter(pytest_case=self).exists():
            raise AutoPytestError(AUTO_PYTEST_GENERAL_TASK_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)
