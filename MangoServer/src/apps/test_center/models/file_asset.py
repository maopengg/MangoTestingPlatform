from django.db import models, router, transaction

from src.apps.user.models import User


class FileData(models.Model):
    """用户主动维护的永久测试文件资产。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    user = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="file_data_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    project_product = models.ForeignKey(
        to="test_center.ProjectProduct",
        to_field="id",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=None,
    )
    type = models.SmallIntegerField(verbose_name="类型")
    name = models.CharField(verbose_name="文件名称", max_length=255, unique=True)
    test_file = models.FileField(verbose_name="文件", upload_to="test_file/", null=True, blank=True)
    failed_screenshot = models.ImageField(
        verbose_name="失败截图",
        upload_to="failed_screenshot/",
        null=True,
        blank=True,
    )
    file_size = models.BigIntegerField(verbose_name="文件大小", default=0)
    allow_download = models.BooleanField(verbose_name="是否允许下载", default=True)

    class Meta:
        db_table = "file_data"

    def delete(self, *args, **kwargs):
        using = kwargs.get('using') or router.db_for_write(type(self), instance=self)
        files = [(field.storage, field.name) for field in (self.test_file, self.failed_screenshot) if field]
        with transaction.atomic(using=using):
            result = super().delete(*args, **kwargs)
            # 文件存储不参与数据库回滚，整批提交后才能实际删除文件。
            for storage, name in files:
                transaction.on_commit(lambda storage=storage, name=name: storage.delete(name),
                                      using=using, robust=True)
        return result
