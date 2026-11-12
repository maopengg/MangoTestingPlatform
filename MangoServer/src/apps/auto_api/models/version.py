from django.db import models

from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiInfoRevision(models.Model):
    """不可变的接口执行配置修订。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    api_info = models.ForeignKey(
        to="ApiInfo",
        to_field='id',
        related_name='revisions',
        on_delete=models.CASCADE,
    )
    revision_no = models.PositiveIntegerField(verbose_name="修订号")
    parent_revision = models.ForeignKey(
        to='self',
        related_name='child_revisions',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    restored_from_revision = models.ForeignKey(
        to='self',
        related_name='restored_revisions',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    snapshot_schema_version = models.PositiveIntegerField(verbose_name="快照结构版本", default=2)
    payload = models.JSONField(verbose_name="不可变接口配置")
    checksum = models.CharField(verbose_name="配置哈希", max_length=64, db_index=True)
    source = models.CharField(verbose_name="变更来源", max_length=32, default='system', db_index=True)
    operator = models.ForeignKey(
        to=User,
        to_field='id',
        verbose_name="操作人",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    summary = models.CharField(verbose_name="变更摘要", max_length=256, null=True, blank=True)

    class Meta:
        db_table = 'api_info_revision'
        ordering = ['-revision_no']
        constraints = [
            models.UniqueConstraint(
                fields=['api_info', 'revision_no'],
                name='uniq_api_info_revision_no',
            ),
        ]
        indexes = [
            models.Index(fields=['api_info', '-revision_no'], name='idx_api_info_revision_no'),
        ]


class ApiInfoRelease(models.Model):
    """接口正式发布记录，精确指向一个不可变接口修订。"""

    STATUS_PUBLISHED = 'published'
    STATUS_DEPRECATED = 'deprecated'
    STATUS_RETIRED = 'retired'

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    api_info = models.ForeignKey(
        to="ApiInfo",
        to_field='id',
        related_name='releases',
        on_delete=models.CASCADE,
    )
    revision = models.ForeignKey(
        to="ApiInfoRevision",
        to_field='id',
        related_name='releases',
        on_delete=models.CASCADE,
    )
    version_no = models.PositiveIntegerField(verbose_name="发布版本号")
    version_label = models.CharField(verbose_name="发布版本", max_length=64)
    status = models.CharField(verbose_name="发布状态", max_length=32, default=STATUS_PUBLISHED, db_index=True)
    is_current = models.BooleanField(verbose_name="是否当前发布版本", default=True, db_index=True)
    # MySQL 不支持条件唯一索引；历史版本使用 NULL，允许保留多条。
    current_unique_marker = models.GeneratedField(
        verbose_name="当前版本唯一标记",
        expression=models.Case(models.When(is_current=True, then=models.Value(1)), default=models.Value(None)),
        output_field=models.SmallIntegerField(), db_persist=True, null=True, blank=True,
    )
    release_note = models.TextField(verbose_name="发布说明", null=True, blank=True)
    published_by = models.ForeignKey(
        to=User,
        to_field='id',
        verbose_name="发布人",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    published_at = models.DateTimeField(verbose_name="发布时间", auto_now_add=True)
    replaced_release = models.ForeignKey(
        to='self',
        related_name='replacement_releases',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = 'api_info_release'
        ordering = ['-version_no']
        constraints = [
            models.UniqueConstraint(
                fields=['api_info', 'version_no'],
                name='uniq_api_info_release_no',
            ),
            models.UniqueConstraint(
                fields=['api_info', 'current_unique_marker'],
                name='uniq_current_api_info_release',
            ),
        ]
        indexes = [
            models.Index(fields=['api_info', 'is_current'], name='idx_info_release_current'),
        ]


class ApiCaseRevision(models.Model):
    """不可变的 API Case 聚合配置修订。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    api_case = models.ForeignKey(
        to="ApiCase",
        to_field='id',
        related_name='revisions',
        on_delete=models.CASCADE,
    )
    revision_no = models.PositiveIntegerField(verbose_name="修订号")
    parent_revision = models.ForeignKey(
        to='self',
        related_name='child_revisions',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    restored_from_revision = models.ForeignKey(
        to='self',
        related_name='restored_revisions',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    snapshot_schema_version = models.PositiveIntegerField(verbose_name="快照结构版本", default=2)
    payload = models.JSONField(verbose_name="不可变用例聚合配置")
    checksum = models.CharField(verbose_name="配置哈希", max_length=64, db_index=True)
    source = models.CharField(verbose_name="变更来源", max_length=32, default='system', db_index=True)
    operator = models.ForeignKey(
        to=User,
        to_field='id',
        verbose_name="操作人",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    summary = models.CharField(verbose_name="变更摘要", max_length=256, null=True, blank=True)
    change_group_id = models.CharField(verbose_name="变更分组ID", max_length=64, null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'api_case_revision'
        ordering = ['-revision_no']
        constraints = [
            models.UniqueConstraint(
                fields=['api_case', 'revision_no'],
                name='uniq_api_case_revision_no',
            ),
        ]
        indexes = [
            models.Index(fields=['api_case', '-revision_no'], name='idx_api_case_revision_no'),
        ]


class ApiCaseRelease(models.Model):
    """Case 的正式发布记录，精确指向一个不可变修订。"""

    STATUS_PUBLISHED = 'published'
    STATUS_DEPRECATED = 'deprecated'
    STATUS_RETIRED = 'retired'

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    api_case = models.ForeignKey(
        to="ApiCase",
        to_field='id',
        related_name='releases',
        on_delete=models.CASCADE,
    )
    revision = models.ForeignKey(
        to="ApiCaseRevision",
        to_field='id',
        related_name='releases',
        on_delete=models.CASCADE,
    )
    version_no = models.PositiveIntegerField(verbose_name="发布版本号")
    version_label = models.CharField(verbose_name="发布版本", max_length=64)
    status = models.CharField(verbose_name="发布状态", max_length=32, default=STATUS_PUBLISHED, db_index=True)
    is_current = models.BooleanField(verbose_name="是否当前发布版本", default=True, db_index=True)
    # 标记由数据库维护，QuerySet.update() 和批量写入也受唯一约束保护。
    current_unique_marker = models.GeneratedField(
        verbose_name="当前版本唯一标记",
        expression=models.Case(models.When(is_current=True, then=models.Value(1)), default=models.Value(None)),
        output_field=models.SmallIntegerField(), db_persist=True, null=True, blank=True,
    )
    release_note = models.TextField(verbose_name="发布说明", null=True, blank=True)
    published_by = models.ForeignKey(
        to=User,
        to_field='id',
        verbose_name="发布人",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    published_at = models.DateTimeField(verbose_name="发布时间", auto_now_add=True)
    replaced_release = models.ForeignKey(
        to='self',
        related_name='replacement_releases',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = 'api_case_release'
        ordering = ['-version_no']
        constraints = [
            models.UniqueConstraint(
                fields=['api_case', 'version_no'],
                name='uniq_api_case_release_no',
            ),
            models.UniqueConstraint(
                fields=['api_case', 'current_unique_marker'],
                name='uniq_current_api_case_release',
            ),
        ]
        indexes = [
            models.Index(fields=['api_case', 'is_current'], name='idx_case_release_current'),
        ]
