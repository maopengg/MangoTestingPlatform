# -*- coding: utf-8 -*-
from django.db import models

from src.apps.user.models import User


class FunctionalTestGridView(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    user = models.ForeignKey(to=User, to_field="id", related_name="functional_test_grid_views",
                             on_delete=models.CASCADE)
    grid_key = models.CharField(verbose_name="表格标识", max_length=64)
    name = models.CharField(verbose_name="视图名称", max_length=128, default="默认视图")
    config = models.JSONField(verbose_name="列顺序、宽度、显隐和冻结配置", default=dict, blank=True)
    is_default = models.BooleanField(verbose_name="默认视图", default=True)

    class Meta:
        db_table = "functional_test_grid_view"
        ordering = ["-is_default", "id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "grid_key", "name"], name="functional_test_grid_view_unique")]
