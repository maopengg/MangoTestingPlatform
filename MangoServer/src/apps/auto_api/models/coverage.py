from django.db import models

from src.apps.auto_api.enums.case import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
)
from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageApiInfoBindingStatus,
    ModuleCoverageCaseStatus,
    ModuleCoverageExecutionResult,
    ModuleCoverageInterfaceStatus,
    ModuleCoverageResolutionStatus,
    ModuleCoverageScanMode,
    ModuleCoverageScanScope,
    ModuleCoverageScanStatus,
    ModuleCoverageSyncAction,
    ModuleCoverageTestOwnership,
    ModuleCoverageValidity,
    ModuleCoveragePolicy,
)
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ModuleCoverageScan(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    include_descendants = models.BooleanField(verbose_name="包含子模块", default=False)
    repository_key = models.CharField(verbose_name="仓库标识", max_length=256)
    repository_name = models.CharField(verbose_name="仓库名称", max_length=256)
    branch = models.CharField(verbose_name="分支", max_length=256)
    commit_sha = models.CharField(verbose_name="提交版本", max_length=64)
    base_commit_sha = models.CharField(verbose_name="增量基线提交", max_length=64, null=True, blank=True)
    test_env = models.SmallIntegerField(verbose_name="被测环境", null=True, blank=True)
    scan_mode = models.CharField(
        verbose_name="扫描模式", max_length=16,
        choices=ModuleCoverageScanMode.choices, default=ModuleCoverageScanMode.FULL,
    )
    scope_type = models.CharField(
        verbose_name="扫描范围", max_length=16,
        choices=ModuleCoverageScanScope.choices, default=ModuleCoverageScanScope.MODULE,
    )
    target_interface = models.ForeignKey(
        to="ModuleCoverageInterfaceSnapshot", related_name="target_scans",
        null=True, blank=True, on_delete=models.PROTECT,
    )
    expected_case_count = models.PositiveIntegerField(verbose_name="预期Case数")
    expected_interface_count = models.PositiveIntegerField(verbose_name="预期接口数", default=0)
    idempotency_key = models.CharField(verbose_name="幂等键", max_length=128, unique=True)
    status = models.CharField(
        verbose_name="扫描状态", max_length=32, db_index=True,
        choices=ModuleCoverageScanStatus.choices, default=ModuleCoverageScanStatus.UPLOADING,
    )
    summary = models.JSONField(verbose_name="扫描汇总", default=dict, blank=True)
    skill_name = models.CharField(max_length=128, default="mango-code-driven-api-case-builder")
    skill_version = models.CharField(max_length=64, default="1")
    schema_version = models.PositiveIntegerField(default=3)
    created_by = models.ForeignKey(
        to=User, to_field="id", related_name="created_module_coverage_scans",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_module_coverage_scan"
        ordering = ["-id"]
        indexes = [
            models.Index(
                fields=["project_product", "module", "repository_key", "branch", "status"],
                name="ft_coverage_scan_scope_idx",
            ),
        ]


class ModuleCoverageCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    repository_key = models.CharField(verbose_name="仓库标识", max_length=256)
    branch = models.CharField(verbose_name="分支", max_length=256)
    source_key = models.CharField(verbose_name="稳定来源Key", max_length=512)
    source_key_hash = models.CharField(
        verbose_name="稳定来源Key哈希",
        max_length=64,
        editable=False,
    )
    interface_source_key = models.CharField(verbose_name="接口稳定来源Key", max_length=512, default="")
    interface_source_key_hash = models.CharField(
        verbose_name="接口稳定来源Key哈希",
        max_length=64,
        editable=False,
        default="",
    )
    name = models.CharField(verbose_name="Case标题", max_length=512)
    interface_name = models.CharField(verbose_name="接口名称", max_length=512)
    method = models.CharField(verbose_name="请求方法", max_length=16)
    url = models.CharField(verbose_name="接口URL", max_length=1024)
    test_ownership = models.CharField(
        verbose_name="测试归属",
        max_length=64,
        choices=ModuleCoverageTestOwnership.choices,
        default=ModuleCoverageTestOwnership.HTTP_API_AUTOMATION,
    )
    scenario_layer = models.SmallIntegerField(
        verbose_name="测试层级",
        choices=ApiCaseScenarioLayerEnum.choices(),
        null=True,
        blank=True,
        db_index=True,
    )
    scenario_type = models.SmallIntegerField(
        verbose_name="验证类型",
        choices=ApiCaseScenarioTypeEnum.choices(),
        null=True,
        blank=True,
        db_index=True,
    )
    scenario_tags = models.JSONField(
        verbose_name="执行场景",
        default=list, blank=True,
        help_text=f"字符串数组，可选值：{ApiCaseScenarioTagEnum.get_key_list()}",
    )
    status = models.CharField(
        verbose_name="当前状态", max_length=32, db_index=True,
        choices=ModuleCoverageCaseStatus.choices,
        default=ModuleCoverageCaseStatus.PENDING_CREATE,
    )
    execution_result = models.CharField(
        verbose_name="执行结果", max_length=32,
        choices=ModuleCoverageExecutionResult.choices,
        default=ModuleCoverageExecutionResult.NOT_EXECUTED,
    )
    coverage_validity = models.CharField(
        verbose_name="覆盖有效性", max_length=24, db_index=True,
        choices=ModuleCoverageValidity.choices, default=ModuleCoverageValidity.VALID,
    )
    coverage_validity_reason = models.TextField(verbose_name="覆盖有效性原因", blank=True, default="")
    last_reviewed_scan = models.ForeignKey(
        to="ModuleCoverageScan", related_name="reviewed_cases",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    api_case = models.ForeignKey(
        to="ApiCase", to_field="id", related_name="module_coverage_cases",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    api_case_revision = models.ForeignKey(
        to="ApiCaseRevision", to_field="id", related_name="module_coverage_cases",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    first_seen_scan = models.ForeignKey(
        to="ModuleCoverageScan", related_name="first_seen_cases", on_delete=models.PROTECT,
    )
    last_seen_scan = models.ForeignKey(
        to="ModuleCoverageScan", related_name="last_seen_cases", on_delete=models.PROTECT,
    )
    current_snapshot = models.ForeignKey(
        to="ModuleCoverageCaseSnapshot", related_name="current_for_cases",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    module_interface = models.ForeignKey(
        to="ModuleCoverageModuleInterface",
        related_name="coverage_cases",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_module_coverage_case"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["module_interface", "source_key_hash"],
                name="api_cov_case_mod_if_src_uniq",
            ),
            models.UniqueConstraint(
                fields=[
                    "project_product", "module", "repository_key", "branch",
                    "interface_source_key_hash", "source_key_hash",
                ],
                name="api_cov_case_legacy_mod_src_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project_product", "module", "status", "-id"],
                name="ft_coverage_case_state_idx",
            ),
        ]


class ModuleCoverageCaseSnapshot(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    scan = models.ForeignKey(to="ModuleCoverageScan", related_name="case_snapshots", on_delete=models.PROTECT)
    coverage_case = models.ForeignKey(to="ModuleCoverageCase", related_name="snapshots", on_delete=models.PROTECT)
    interface_snapshot = models.ForeignKey(
        to="ModuleCoverageInterfaceSnapshot", related_name="case_snapshots",
        null=True, blank=True, on_delete=models.PROTECT,
    )
    content_hash = models.CharField(verbose_name="规范内容哈希", max_length=64, db_index=True)
    submitted_hash = models.CharField(verbose_name="上传内容哈希", max_length=64)
    payload = models.JSONField(verbose_name="Case台账与覆盖路径快照", default=dict, blank=True)
    api_case = models.ForeignKey(
        to="ApiCase", to_field="id", related_name="module_coverage_snapshots",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    api_case_revision = models.ForeignKey(
        to="ApiCaseRevision", to_field="id", related_name="module_coverage_snapshots",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    sync_action = models.CharField(max_length=16, choices=ModuleCoverageSyncAction.choices)
    message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "api_module_coverage_case_snapshot"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["scan", "coverage_case"],
                name="ft_coverage_scan_case_unique",
            ),
        ]


class ModuleCoverageModuleInterface(models.Model):
    """A stable consumer-module relationship to a discovered interface asset."""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    repository_key = models.CharField(verbose_name="仓库标识", max_length=256)
    branch = models.CharField(verbose_name="分支", max_length=256)
    source_key = models.CharField(verbose_name="接口稳定来源Key", max_length=512)
    source_key_hash = models.CharField(verbose_name="接口稳定来源Key哈希", max_length=64, editable=False)
    coverage_policy = models.CharField(verbose_name="覆盖策略", max_length=16,
                                       choices=ModuleCoveragePolicy.choices, default=ModuleCoveragePolicy.INCLUDED)
    coverage_reason = models.TextField(verbose_name="覆盖策略处理原因", blank=True, default="")
    api_info = models.ForeignKey(
        to="ApiInfo", to_field="id", related_name="module_coverage_consumers",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    api_info_revision = models.ForeignKey(
        to="ApiInfoRevision", to_field="id", related_name="module_coverage_consumers",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    current_snapshot = models.ForeignKey(
        to="ModuleCoverageInterfaceSnapshot", related_name="current_for_module_interfaces",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    first_seen_scan = models.ForeignKey(
        to="ModuleCoverageScan", related_name="first_seen_module_interfaces", on_delete=models.PROTECT,
    )
    last_seen_scan = models.ForeignKey(
        to="ModuleCoverageScan", related_name="last_seen_module_interfaces", on_delete=models.PROTECT,
    )
    api_info_binding_status = models.CharField(
        verbose_name="ApiInfo绑定状态", max_length=16, db_index=True,
        choices=ModuleCoverageApiInfoBindingStatus.choices,
        default=ModuleCoverageApiInfoBindingStatus.UNBOUND,
    )
    api_info_binding_reason = models.TextField(verbose_name="ApiInfo绑定说明", blank=True, default="")
    lifecycle_status = models.CharField(
        verbose_name="接口生命周期", max_length=16, db_index=True,
        choices=ModuleCoverageInterfaceStatus.choices,
        default=ModuleCoverageInterfaceStatus.ACTIVE,
    )
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_module_coverage_module_interface"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "project_product", "module", "repository_key", "branch", "source_key_hash",
                ],
                name="api_cov_mod_if_scope_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project_product", "module", "repository_key", "branch", "lifecycle_status"],
                name="api_cov_mod_if_scope_idx",
            ),
            models.Index(
                fields=["project_product", "api_info", "lifecycle_status"],
                name="api_cov_mod_if_api_idx",
            ),
            models.Index(fields=["last_seen_scan"], name="api_cov_mod_if_seen_idx"),
            models.Index(
                fields=["project_product", "repository_key", "branch", "source_key_hash"],
                name="api_cov_if_identity_idx",
            ),
        ]


class ModuleCoverageInterfaceSnapshot(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    scan = models.ForeignKey(
        to="ModuleCoverageScan",
        related_name="interface_snapshots",
        on_delete=models.PROTECT,
    )
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    module_interface = models.ForeignKey(
        to="ModuleCoverageModuleInterface",
        related_name="snapshots",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    repository_key = models.CharField(verbose_name="仓库标识", max_length=256)
    branch = models.CharField(verbose_name="分支", max_length=256)
    source_key = models.CharField(verbose_name="接口稳定来源Key", max_length=512)
    source_key_hash = models.CharField(verbose_name="接口稳定来源Key哈希", max_length=64, editable=False)
    interface_name = models.CharField(verbose_name="接口名称", max_length=512)
    method = models.CharField(verbose_name="请求方法", max_length=16)
    url = models.CharField(verbose_name="接口URL", max_length=1024)
    mermaid = models.TextField(verbose_name="接口调用流程", blank=True, default="")
    node_ids = models.JSONField(verbose_name="流程节点ID", default=list, blank=True)
    branch_ids = models.JSONField(verbose_name="流程分支ID", default=list, blank=True)
    resolution_status = models.CharField(
        verbose_name="链路解析状态", max_length=16, db_index=True,
        choices=ModuleCoverageResolutionStatus.choices,
        default=ModuleCoverageResolutionStatus.RESOLVED,
    )
    resolution_reason = models.TextField(verbose_name="链路解析原因", blank=True, default="")
    gap_reason = models.TextField(verbose_name="未解析原因", blank=True, default="")
    next_action = models.TextField(verbose_name="下一步处理", blank=True, default="")
    resumption_point = models.TextField(verbose_name="恢复扫描位置", blank=True, default="")
    api_info = models.ForeignKey(
        to="ApiInfo", to_field="id", related_name="module_coverage_interface_snapshots",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    api_info_revision = models.ForeignKey(
        to="ApiInfoRevision", to_field="id", related_name="module_coverage_interface_snapshots",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    api_info_binding_status = models.CharField(
        verbose_name="ApiInfo绑定状态", max_length=16, db_index=True,
        choices=ModuleCoverageApiInfoBindingStatus.choices,
        default=ModuleCoverageApiInfoBindingStatus.UNBOUND,
    )
    api_info_binding_reason = models.TextField(verbose_name="ApiInfo绑定说明", blank=True, default="")
    content_hash = models.CharField(verbose_name="规范内容哈希", max_length=64, db_index=True)
    submitted_hash = models.CharField(verbose_name="上传内容哈希", max_length=64)
    sync_action = models.CharField(max_length=16, choices=ModuleCoverageSyncAction.choices)
    lifecycle_status = models.CharField(
        verbose_name="接口生命周期", max_length=16, db_index=True,
        choices=ModuleCoverageInterfaceStatus.choices,
        default=ModuleCoverageInterfaceStatus.ACTIVE,
    )
    is_current = models.BooleanField(verbose_name="是否当前接口快照", default=False, db_index=True)
    removed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "api_module_coverage_interface_snapshot"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["scan", "module", "source_key_hash"],
                name="ft_coverage_scan_interface_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project_product", "module", "repository_key", "branch", "source_key_hash", "-id"],
                name="ft_cov_interface_scope_idx",
            ),
        ]
