# -*- coding: utf-8 -*-
from django.db import models

from src.apps.functional_test.enums import (
    FunctionalTestContextContentTypeEnum,
    FunctionalTestContextKeyEnum,
    FunctionalTestContextParseStatusEnum,
    FunctionalTestContextUrlTypeEnum,
)
from src.apps.test_center.models import FileData
from src.apps.user.models import User


class FunctionalTestContextResource(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    suite = models.ForeignKey(to="ManualTestSuite", to_field="id", on_delete=models.CASCADE)
    context_key = models.SmallIntegerField(
        verbose_name="上下文分组",
        choices=FunctionalTestContextKeyEnum.choices(),
        db_index=True,
    )
    content_type = models.SmallIntegerField(
        verbose_name="资料类型",
        choices=FunctionalTestContextContentTypeEnum.choices(),
        default=FunctionalTestContextContentTypeEnum.TEXT.value,
        db_index=True,
    )
    url_type = models.SmallIntegerField(
        verbose_name="URL类型",
        choices=FunctionalTestContextUrlTypeEnum.choices(),
        default=FunctionalTestContextUrlTypeEnum.NORMAL.value,
    )
    title = models.CharField(verbose_name="资料标题", max_length=256)
    content = models.TextField(verbose_name="文本或URL内容", null=True, blank=True)
    file = models.ForeignKey(to=FileData, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024, null=True, blank=True)
    file_name = models.CharField(verbose_name="文件名称", max_length=255, null=True, blank=True)
    mime_type = models.CharField(verbose_name="MIME类型", max_length=128, null=True, blank=True)
    file_size = models.IntegerField(verbose_name="文件大小", null=True, blank=True)
    extracted_text = models.TextField(verbose_name="解析文本", null=True, blank=True)
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    parse_status = models.SmallIntegerField(
        verbose_name="解析状态",
        choices=FunctionalTestContextParseStatusEnum.choices(),
        default=FunctionalTestContextParseStatusEnum.NOT_PARSED.value,
    )
    parse_error = models.TextField(verbose_name="解析失败原因", null=True, blank=True)
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_context_resource_create_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_context_resource_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "functional_test_context_resource"
        ordering = ["suite_id", "context_key", "id"]
        indexes = [
            models.Index(fields=["suite", "context_key", "enabled"]),
        ]
