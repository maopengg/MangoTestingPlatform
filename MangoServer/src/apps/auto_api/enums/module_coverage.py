from django.db import models

from src.common.enums.base import BaseEnum


class ModuleCoverageErrorCodeEnum(BaseEnum):
    INTERFACE_NOT_FOUND = "MODULE_COVERAGE_INTERFACE_NOT_FOUND"


class ModuleCoverageScanMode(models.TextChoices):
    FULL = "full", "完整扫描"
    INCREMENTAL = "incremental", "增量扫描"


class ModuleCoverageScanScope(models.TextChoices):
    PROJECT = "project", "项目接口盘点"
    MODULE = "module", "模块扫描"
    INTERFACE = "interface", "单接口扫描"


class ModuleCoverageScanStatus(models.TextChoices):
    UPLOADING = "uploading", "上传中"
    COMPLETED = "completed", "已完成"
    COMPLETED_WITH_GAPS = "completed_with_gaps", "审计完成（存在Gap）"
    CANCELLED = "cancelled", "已取消"


class ModuleCoverageCaseStatus(models.TextChoices):
    PENDING_CREATE = "pending_create", "待创建"
    COMPLETED = "completed", "已完成"
    DEFERRED = "deferred", "暂不处理"
    REMOVED = "removed", "已移除"


class ModuleCoverageTestOwnership(models.TextChoices):
    HTTP_API_AUTOMATION = "HTTP API自动化", "HTTP API自动化"
    UNIT_TEST = "单元测试", "单元测试"
    INTEGRATION_TEST = "集成测试", "集成测试"


class ModuleCoverageInterfaceStatus(models.TextChoices):
    ACTIVE = "active", "有效"
    REMOVED = "removed", "已移除"


class ModuleCoverageValidity(models.TextChoices):
    VALID = "valid", "有效"
    PENDING_REVIEW = "pending_review", "待复核"
    INVALID = "invalid", "已失效"


class ModuleCoverageInterfaceCoverageStatus(models.TextChoices):
    COVERED = "covered", "已覆盖"
    PARTIAL = "partial", "部分覆盖"
    UNCOVERED = "uncovered", "未覆盖"
    DEFERRED = "deferred", "暂不处理"


class ModuleCoveragePolicy(models.TextChoices):
    INCLUDED = "included", "纳入覆盖"
    DEFERRED = "deferred", "暂不处理"
    EXCLUDED = "excluded", "排除覆盖"


class ModuleCoverageResolutionStatus(models.TextChoices):
    RESOLVED = "resolved", "链路完整"
    PLACEHOLDER = "placeholder", "占位图"
    GAP = "gap", "未解析Gap"


class ModuleCoverageInventoryStatus(models.TextChoices):
    COMPLETED = "completed", "已盘点"
    REVIEW = "review", "版本待复核"
    PENDING = "pending", "未盘点"


class ModuleCoverageAnalysisStatus(models.TextChoices):
    COMPLETED = "completed", "已分析"
    PENDING = "pending", "待分析"
    REVIEW = "review", "版本待复核"
    GAP = "gap", "分析不完整"
    DEFERRED = "deferred", "暂缓分析"
    EXCLUDED = "excluded", "已排除"


class ModuleCoverageApiInfoBindingStatus(models.TextChoices):
    BOUND = "bound", "已绑定"
    UNBOUND = "unbound", "未绑定"
    AMBIGUOUS = "ambiguous", "候选冲突"
    MISMATCH = "mismatch", "定义不匹配"


class ModuleCoverageSyncAction(models.TextChoices):
    CREATED = "created", "新增"
    UPDATED = "updated", "修改"
    UNCHANGED = "unchanged", "未变化"
    REMOVED = "removed", "移除"


class ModuleCoverageExecutionResult(models.TextChoices):
    PASSED = "passed", "执行通过"
    FAILED = "failed", "执行失败"
    PARTIAL = "partial", "部分通过"
    NOT_APPLICABLE = "not_applicable", "不适用"
    NOT_EXECUTED = "not_executed", "未执行"
