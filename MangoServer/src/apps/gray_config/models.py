# -*- coding: utf-8 -*-
from django.db import models
from mangotools.enums import StatusEnum

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter
from src.apps.auto_ui.models import UiCase
from src.apps.data_factory.models import DataFactoryDatasourceAlias
from src.apps.data_factory.models import Database
from src.apps.gray_config.enums import GrayExecutionLockStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_FILE_RELATION_DELETE_BINDING_GRAY_INVALID,
    GRAY_RELATION_DELETE_BINDING_GRAY_INVALID,
    GRAY_CASE_CONFIG_RELATION_DELETE_BINDING_INVALID,
    GrayConfigError,
)
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.models import User


class GrayRepository(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="仓库名称", max_length=128)
    repo_url = models.CharField(verbose_name="Git仓库地址", max_length=512)
    provider = models.CharField(verbose_name="Git平台类型", max_length=32, default="gitlab")
    api_base_url = models.CharField(verbose_name="Git平台域名", max_length=256)
    access_token = models.CharField(verbose_name="Git平台访问令牌", max_length=512, null=True, blank=True)
    branch = models.CharField(verbose_name="分支", max_length=128)
    test_env = models.SmallIntegerField(verbose_name="测试环境", null=True, blank=True, default=None)
    config_dirs = models.JSONField(verbose_name="配置文件目录", default=list, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value)
    description = models.TextField(verbose_name="说明", null=True, blank=True)
    last_update_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="最后更新人",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "gray_repository"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["test_env", "status"]),
            models.Index(fields=["provider", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["test_env", "name"], name="uniq_gray_repository_env_name"),
        ]

    def delete(self, *args, **kwargs):
        if GrayYamlFileBinding.objects.filter(repository=self).exists():
            raise GrayConfigError(GRAY_FILE_RELATION_DELETE_BINDING_GRAY_INVALID)
        super().delete(*args, **kwargs)


class GrayYamlFile(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="YAML名称", max_length=128)
    effect_wait_seconds = models.IntegerField(verbose_name="生效等待秒数", default=10)
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value)
    last_update_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="最后更新人",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "gray_yaml_file"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["project_product", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["project_product", "name"], name="uniq_gray_yaml_file_product_name"),
        ]

    def delete(self, *args, **kwargs):
        if GrayFeature.objects.filter(yaml_file=self).exists():
            raise GrayConfigError(GRAY_RELATION_DELETE_BINDING_GRAY_INVALID)
        if GrayYamlFileBinding.objects.filter(yaml_file=self).exists():
            raise GrayConfigError(GRAY_RELATION_DELETE_BINDING_GRAY_INVALID)
        super().delete(*args, **kwargs)


class GrayYamlFileBinding(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    yaml_file = models.ForeignKey(to=GrayYamlFile, to_field="id", on_delete=models.CASCADE)
    repository = models.ForeignKey(to=GrayRepository, to_field="id", on_delete=models.PROTECT)
    file_path = models.CharField(verbose_name="仓库内文件路径", max_length=512)
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value)
    last_update_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="最后更新人",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "gray_yaml_file_binding"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["yaml_file", "status"]),
            models.Index(fields=["repository", "status"]),
            models.Index(fields=["repository", "file_path"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["yaml_file", "repository"], name="uniq_gray_yaml_binding_file_repo"),
        ]


class GrayFeature(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    gray_code = models.CharField(verbose_name="灰度编号", max_length=64)
    config_type = models.SmallIntegerField(verbose_name="配置类型", default=1)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    yaml_file = models.ForeignKey(to=GrayYamlFile, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    datasource_alias = models.ForeignKey(
        to=DataFactoryDatasourceAlias,
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    database = models.ForeignKey(to=Database, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(verbose_name="灰度名称", max_length=128)
    feature_key = models.CharField(verbose_name="灰度Key", max_length=256)
    path_config = models.JSONField(verbose_name="YAML路径配置", default=list, blank=True)
    enable_sql = models.TextField(verbose_name="开启SQL", null=True, blank=True)
    disable_sql = models.TextField(verbose_name="关闭SQL", null=True, blank=True)
    restore_sql = models.TextField(verbose_name="恢复SQL", null=True, blank=True)
    enable_code = models.TextField(verbose_name="开启代码", null=True, blank=True)
    disable_code = models.TextField(verbose_name="关闭代码", null=True, blank=True)
    restore_code = models.TextField(verbose_name="恢复代码", null=True, blank=True)
    default_restore = models.BooleanField(verbose_name="默认执行后恢复", default=True)
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value)
    description = models.TextField(verbose_name="说明", null=True, blank=True)
    last_update_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="最后更新人",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "gray_feature"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["project_product", "module"]),
            models.Index(fields=["config_type", "status"]),
            models.Index(fields=["feature_key"]),
            models.Index(fields=["yaml_file", "status"]),
            models.Index(fields=["database", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["gray_code"], name="uniq_gray_feature_code"),
        ]

    def delete(self, *args, **kwargs):
        if AutomationCaseGrayConfig.objects.filter(gray_feature=self).exists():
            raise GrayConfigError(GRAY_CASE_CONFIG_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class AutomationCaseGrayConfig(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case_type = models.SmallIntegerField(verbose_name="用例类型")
    scope = models.CharField(verbose_name="绑定范围", max_length=32, default="case")
    api_case = models.ForeignKey(to=ApiCase, to_field="id", on_delete=models.CASCADE, null=True, blank=True)
    ui_case = models.ForeignKey(to=UiCase, to_field="id", on_delete=models.CASCADE, null=True, blank=True)
    api_case_detailed = models.ForeignKey(
        to=ApiCaseDetailed,
        to_field="id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    api_case_detailed_parameter = models.ForeignKey(
        to=ApiCaseDetailedParameter,
        to_field="id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    gray_feature = models.ForeignKey(to=GrayFeature, to_field="id", on_delete=models.PROTECT)
    target_value = models.CharField(verbose_name="目标值", max_length=128, blank=True, default="")
    action = models.CharField(verbose_name="执行动作", max_length=32, default="enable")
    restore_after_execute = models.BooleanField(verbose_name="执行后恢复", default=True)
    wait_seconds = models.IntegerField(verbose_name="等待秒数", default=0)
    sort = models.IntegerField(verbose_name="排序", default=0)
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value)
    last_update_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="最后更新人",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "automation_case_gray_config"
        ordering = ["sort", "id"]
        indexes = [
            models.Index(fields=["case_type", "scope", "status"]),
            models.Index(fields=["api_case", "status"]),
            models.Index(fields=["ui_case", "status"]),
            models.Index(fields=["api_case_detailed", "status"]),
            models.Index(fields=["api_case_detailed_parameter", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["case_type", "scope", "api_case", "gray_feature", "target_value"],
                name="uniq_api_case_gray_config",
            ),
            models.UniqueConstraint(
                fields=["case_type", "scope", "ui_case", "gray_feature", "target_value"],
                name="uniq_ui_case_gray_config",
            ),
            models.UniqueConstraint(
                fields=["case_type", "scope", "api_case_detailed", "gray_feature", "target_value"],
                name="uniq_api_step_gray_config",
            ),
            models.UniqueConstraint(
                fields=["case_type", "scope", "api_case_detailed_parameter", "gray_feature", "target_value"],
                name="uniq_api_param_gray_config",
            ),
        ]


class GrayExecutionLog(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite_id = models.BigIntegerField(verbose_name="测试报告ID", null=True, blank=True)
    test_suite_detail_id = models.BigIntegerField(verbose_name="执行明细ID", null=True, blank=True)
    case_type = models.SmallIntegerField(verbose_name="用例类型", null=True, blank=True)
    case_id = models.BigIntegerField(verbose_name="用例ID", null=True, blank=True)
    case_name = models.CharField(verbose_name="用例名称", max_length=256, null=True, blank=True)
    api_case_detailed_id = models.BigIntegerField(verbose_name="API步骤ID", null=True, blank=True)
    api_case_detailed_name = models.CharField(verbose_name="API步骤名称", max_length=256, null=True, blank=True)
    api_case_detailed_parameter_id = models.BigIntegerField(verbose_name="API参数场景ID", null=True, blank=True)
    api_case_detailed_parameter_name = models.CharField(verbose_name="API参数场景名称", max_length=256, null=True,
                                                        blank=True)
    gray_config_id = models.BigIntegerField(verbose_name="用例灰度配置ID", null=True, blank=True)
    gray_feature = models.ForeignKey(to=GrayFeature, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    yaml_file_binding = models.ForeignKey(
        to=GrayYamlFileBinding,
        to_field="id",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    repository = models.ForeignKey(to=GrayRepository, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    config_type = models.SmallIntegerField(verbose_name="配置类型")
    yaml_file = models.ForeignKey(to=GrayYamlFile, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    database = models.ForeignKey(to=Database, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    feature_key = models.CharField(verbose_name="灰度Key", max_length=256)
    target_value = models.CharField(verbose_name="目标值", max_length=128, null=True, blank=True)
    action = models.CharField(verbose_name="执行动作", max_length=32)
    before_snapshot = models.JSONField(verbose_name="执行前快照", null=True, blank=True)
    after_snapshot = models.JSONField(verbose_name="执行后快照", null=True, blank=True)
    commit_hash = models.CharField(verbose_name="提交Hash", max_length=128, null=True, blank=True)
    restore_commit_hash = models.CharField(verbose_name="恢复提交Hash", max_length=128, null=True, blank=True)
    source_branch = models.CharField(verbose_name="来源分支", max_length=256, null=True, blank=True)
    target_branch = models.CharField(verbose_name="目标分支", max_length=256, null=True, blank=True)
    merge_request_id = models.CharField(verbose_name="合并请求ID", max_length=128, null=True, blank=True)
    merge_request_iid = models.CharField(verbose_name="合并请求IID", max_length=128, null=True, blank=True)
    merge_request_url = models.CharField(verbose_name="合并请求地址", max_length=512, null=True, blank=True)
    merge_request_state = models.CharField(verbose_name="合并请求状态", max_length=64, null=True, blank=True)
    affected_rows = models.IntegerField(verbose_name="影响行数", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=0)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    started_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)

    class Meta:
        db_table = "gray_execution_log"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["case_type", "case_id", "create_time"]),
            models.Index(fields=["test_suite_id", "create_time"]),
            models.Index(fields=["gray_feature", "create_time"]),
            models.Index(fields=["status", "create_time"]),
        ]


class GrayExecutionLock(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    lock_key = models.CharField(verbose_name="锁标识", max_length=256, unique=True)
    repository = models.ForeignKey(to=GrayRepository, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.CharField(verbose_name="分支", max_length=128, null=True, blank=True)
    owner_type = models.CharField(verbose_name="占用方类型", max_length=32, null=True, blank=True)
    owner_id = models.CharField(verbose_name="占用方ID", max_length=128, null=True, blank=True)
    execution_log_id = models.BigIntegerField(verbose_name="灰度执行记录ID", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=GrayExecutionLockStatusEnum.RELEASED.value)
    locked_at = models.DateTimeField(verbose_name="锁定时间", null=True, blank=True)
    expired_at = models.DateTimeField(verbose_name="过期时间", null=True, blank=True)
    released_at = models.DateTimeField(verbose_name="释放时间", null=True, blank=True)
    node_name = models.CharField(verbose_name="节点名称", max_length=128, null=True, blank=True)
    remark = models.CharField(verbose_name="备注", max_length=512, null=True, blank=True)

    class Meta:
        db_table = "gray_execution_lock"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["repository", "branch"]),
            models.Index(fields=["status", "expired_at"]),
        ]
