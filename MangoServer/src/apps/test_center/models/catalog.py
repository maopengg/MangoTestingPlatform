from django.db import models, transaction
from django.db.models.deletion import ProtectedError

from src.apps.test_center.exceptions import (
    PRODUCT_MODULE_COVERAGE_DELETE_PROTECTED,
    PRODUCT_MODULE_DELETE_PROTECTED,
    TestCenterError,
)

from src.apps.system.exceptions import (
    SYSTEM_CATALOG_PROJECT_PRODUCT_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_NOTICE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_MODULE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_API_INFO_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_CASE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_PARAMETER_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_REQUEST_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_PAGE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_STEP_PAGE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_CASE_RELATION_DELETE_BINDING_INVALID_CODE_CASE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_PARAMETER_RELATION_DELETE_BINDING_INVALID_CODE_PARAMETER_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_TASK_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_RELATION_DELETE_BINDING_INVALID_CODE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_MODULE_RELATION_DELETE_BINDING_INVALID_CODE_MODULE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_API_INFO_RELATION_DELETE_BINDING_INVALID_CODE_API_INFO_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_API_CASE_DELETE_PROTECTED,
    SYSTEM_UI_CASE_DELETE_PROTECTED,
    SYSTEM_CATALOG_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_PAGE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_STEP_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_PYTEST_CASE_DELETE_PROTECTED,
    SYSTEM_CATALOG_ENTITY_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_STATUS_TEMPLATE_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_RECORD_RELATION_EXECUTION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_TASK_RELATION_DELETE_BINDING_INVALID_CODE_TASK_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_CATALOG_REQUIREMENT_RELATION_DELETE_BINDING_INVALID,
    SYSTEM_FUNCTIONAL_CASE_DELETE_PROTECTED,
    SystemError,
)
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""

from django.apps import apps


class Project(models.Model):
    """项目表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="project_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="项目名称", max_length=64, unique=True)
    status = models.SmallIntegerField(verbose_name="状态", default=1)

    class Meta:
        db_table = 'project'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if ProjectProduct.objects.filter(project=self).exists():
            raise SystemError(SYSTEM_CATALOG_PROJECT_PRODUCT_RELATION_DELETE_BINDING_INVALID)
        if NoticeGroup.objects.filter(project=self).exists():
            raise SystemError(SYSTEM_CATALOG_NOTICE_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class ProjectProduct(models.Model):
    """项目产品表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to="Project", to_field="id", on_delete=models.PROTECT)
    owners = models.ManyToManyField(
        to=User,
        related_name="owned_project_products",
        verbose_name="产品负责人列表",
        blank=True,
    )
    update_user = models.ForeignKey(to=User, to_field="id", related_name="project_product_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="产品名称", max_length=64)
    description = models.TextField(verbose_name="产品说明", max_length=5000, blank=True, default='')
    ui_client_type = models.SmallIntegerField(verbose_name="UI客户端类型", default=0)
    api_client_type = models.SmallIntegerField(verbose_name="API客户端类型", default=0)

    class Meta:
        db_table = 'project_product'
        ordering = ['-id']
        unique_together = ('project', 'name')

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if ProductModule.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_MODULE_RELATION_DELETE_BINDING_INVALID)
        if TestObject.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_RELATION_DELETE_BINDING_INVALID)
        from src.apps.auto_api.models import ApiPublic, ApiCase, ApiInfo, ApiHeaders
        if ApiInfo.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_API_INFO_RELATION_DELETE_BINDING_INVALID)
        if ApiCase.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_CASE_RELATION_DELETE_BINDING_INVALID)
        if ApiPublic.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_PARAMETER_RELATION_DELETE_BINDING_INVALID)
        if ApiHeaders.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_REQUEST_RELATION_DELETE_BINDING_INVALID)
        from src.apps.auto_ui.models import UiPublic, UiCase, PageSteps, Page
        if Page.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_PAGE_RELATION_DELETE_BINDING_INVALID)
        if PageSteps.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_STEP_PAGE_RELATION_DELETE_BINDING_INVALID)
        if UiCase.objects.filter(project_product=self).exists():
            raise SystemError(
                SYSTEM_CATALOG_CASE_RELATION_DELETE_BINDING_INVALID_CODE_CASE_RELATION_DELETE_BINDING_INVALID)
        if UiPublic.objects.filter(project_product=self).exists():
            raise SystemError(
                SYSTEM_CATALOG_PARAMETER_RELATION_DELETE_BINDING_INVALID_CODE_PARAMETER_RELATION_DELETE_BINDING_INVALID)
        if apps.get_model("task_center", "Tasks").objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_TASK_RELATION_DELETE_BINDING_INVALID)
        from src.apps.auto_pytest.models import PytestProduct
        if PytestProduct.objects.filter(project_product=self).exists():
            raise SystemError(SYSTEM_CATALOG_RELATION_DELETE_BINDING_INVALID_CODE_RELATION_DELETE_BINDING_INVALID)
        if apps.get_model("test_center", "TestSuiteDetails").objects.filter(project_product=self).exists():
            apps.get_model("test_center", "TestSuiteDetails").objects.filter(project_product=self).delete()
        if apps.get_model("test_center", "TestSuite").objects.filter(project_product=self).exists():
            apps.get_model("test_center", "TestSuite").objects.filter(project_product=self).delete()
        if apps.get_model("test_center", "FileData").objects.filter(project_product=self).exists():
            apps.get_model("test_center", "FileData").objects.filter(project_product=self).delete()
        super().delete(*args, **kwargs)


class ProductModule(models.Model):
    """ 产品模块表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to="ProjectProduct", to_field="id", on_delete=models.PROTECT)
    parent = models.ForeignKey(
        to="self",
        to_field="id",
        related_name="children",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    update_user = models.ForeignKey(to=User, to_field="id", related_name="product_module_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="模块名称", max_length=64)
    # 首次数据迁移前允许为空；存量数据回填后再由用户收紧为非空。
    level = models.PositiveSmallIntegerField(verbose_name="模块层级", null=True, blank=True, db_index=True)
    sort = models.IntegerField(verbose_name="排序", default=0)
    superior_module_1 = models.CharField(verbose_name="一级模块模块名称", max_length=64, null=True, blank=True)
    superior_module_2 = models.CharField(verbose_name="二级模块模块名称", max_length=64, null=True, blank=True)

    class Meta:
        db_table = 'product_module'
        ordering = ['sort', 'id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(level__isnull=True) | models.Q(level__in=[1, 2, 3]),
                name="product_module_level_valid",
            ),
            models.UniqueConstraint(
                fields=["project_product", "parent", "name"],
                name="product_module_parent_name_unique",
            ),
        ]

    def get_full_path(self):
        names = []
        visited = set()
        current = self
        while current:
            identity = current.pk if current.pk is not None else id(current)
            if identity in visited:
                break
            visited.add(identity)
            if current.name:
                names.append(current.name)
            current = current.parent if current.parent_id else None
        return '/'.join(reversed(names))

    def delete(self, *args, **kwargs):
        if self.children.exists():
            raise SystemError(
                SYSTEM_CATALOG_MODULE_RELATION_DELETE_BINDING_INVALID_CODE_MODULE_RELATION_DELETE_BINDING_INVALID)
        from src.apps.auto_api.models import ApiCase, ApiInfo
        if ApiInfo.objects.filter(module=self).exists():
            raise SystemError(
                SYSTEM_CATALOG_API_INFO_RELATION_DELETE_BINDING_INVALID_CODE_API_INFO_RELATION_DELETE_BINDING_INVALID)
        if ApiCase.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_API_CASE_DELETE_PROTECTED)
        from src.apps.auto_ui.models import UiCase, PageSteps, Page
        if UiCase.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_UI_CASE_DELETE_PROTECTED)
        if Page.objects.filter(module=self).exists():
            raise SystemError(
                SYSTEM_CATALOG_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_PAGE_RELATION_DELETE_BINDING_INVALID)
        if PageSteps.objects.filter(module=self).exists():
            raise SystemError(
                SYSTEM_CATALOG_STEP_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID)
        from src.apps.auto_pytest.models import PytestCase
        if PytestCase.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_PYTEST_CASE_DELETE_PROTECTED)
        from src.apps.data_factory.models import DataFactoryEntity, DataFactoryExecution, DataFactoryTemplate
        if DataFactoryEntity.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_CATALOG_ENTITY_RELATION_DELETE_BINDING_INVALID)
        if DataFactoryTemplate.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_CATALOG_STATUS_TEMPLATE_RELATION_DELETE_BINDING_INVALID)
        if DataFactoryExecution.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_CATALOG_RECORD_RELATION_EXECUTION_DELETE_BINDING_INVALID)
        if apps.get_model("task_center", "Tasks").objects.filter(module=self).exists():
            raise SystemError(
                SYSTEM_CATALOG_TASK_RELATION_DELETE_BINDING_INVALID_CODE_TASK_RELATION_DELETE_BINDING_INVALID)
        from src.apps.functional_test.models import ManualTestCase, ManualTestSuite
        if ManualTestSuite.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_CATALOG_REQUIREMENT_RELATION_DELETE_BINDING_INVALID)
        if ManualTestCase.objects.filter(module=self).exists():
            raise SystemError(SYSTEM_FUNCTIONAL_CASE_DELETE_PROTECTED)
        try:
            super().delete(*args, **kwargs)
        except ProtectedError as error:
            from src.apps.auto_api.models import (
                ModuleCoverageCase, ModuleCoverageInterfaceSnapshot, ModuleCoverageModuleInterface, ModuleCoverageScan,
            )
            coverage_models = (ModuleCoverageCase, ModuleCoverageInterfaceSnapshot,
                               ModuleCoverageModuleInterface, ModuleCoverageScan)
            definition = (PRODUCT_MODULE_COVERAGE_DELETE_PROTECTED
                          if any(isinstance(item, coverage_models) for item in error.protected_objects)
                          else PRODUCT_MODULE_DELETE_PROTECTED)
            raise TestCenterError(definition) from error


class TestObject(models.Model):
    """测试对象"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to="ProjectProduct", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="test_object_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    environment = models.SmallIntegerField(verbose_name="环境备注")
    name = models.CharField(verbose_name="被测试的对象", max_length=64)
    value = models.CharField(verbose_name="被测试的对象", max_length=1024, blank=True, default='')
    target_config = models.JSONField(verbose_name="测试地址配置", default=dict, blank=True)
    db_c_status = models.SmallIntegerField(verbose_name="查询权限", default=0)
    db_rud_status = models.SmallIntegerField(verbose_name="增删改权限", default=0)
    auto_type = models.SmallIntegerField(verbose_name="自动化使用类型", default=0)

    class Meta:
        db_table = 'test_object'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class NoticeGroup(models.Model):
    """通知组表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to="Project", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="notice_group_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="通知组名称", max_length=64)
    mail = models.JSONField(verbose_name="邮箱", default=list, blank=True)
    feishu = models.CharField(verbose_name="飞书通知", max_length=255, null=True, blank=True)
    dingding = models.CharField(verbose_name="钉钉通知", max_length=255, null=True, blank=True)
    work_weixin = models.CharField(verbose_name="企业微信通知", max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'notice_group'
        ordering = ['-id']
