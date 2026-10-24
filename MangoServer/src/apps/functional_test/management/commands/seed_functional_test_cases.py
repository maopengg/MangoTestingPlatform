# -*- coding: utf-8 -*-
import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Count
from itertools import islice

from src.apps.auto_api.enums.case import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTypeEnum,
)
from src.apps.functional_test.enums import (
    FunctionalCaseStatusEnum,
    ManualTestAutomationImpactStatusEnum,
    ManualTestChangeStatusEnum,
    ManualTestTypeEnum,
)
from src.apps.functional_test.models import ManualTestCase
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User


class Command(BaseCommand):
    help = "仅向 dev 数据库批量写入功能测试用例；默认目标数量为 50000 条"

    DEFAULT_COUNT = 50_000
    DEFAULT_BATCH_SIZE = 2_000
    DEFAULT_SEED_KEY = "dev-functional-case-50k"
    SEED_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,48}$")
    CASE_NO_PATTERN = re.compile(r"^FT-(\d+)$")

    CATEGORY_PATHS = (
        ("认证与权限", "账号登录", "正常登录"),
        ("认证与权限", "角色权限", "越权校验"),
        ("订单管理", "订单流程", "订单创建"),
        ("订单管理", "订单流程", "订单取消"),
        ("产品管理", "产品配置", "基础信息"),
        ("协议兼容", "HTTP协议", "请求响应"),
        ("协议兼容", "异步消息", "断线重连"),
        ("数据一致性", "批量处理", "边界数据"),
    )
    SCENARIO_TAGS = (
        "routine_regression",
        "smoke_verification",
        "release_verification",
        "data_verification",
    )
    TEST_TYPE_SETS = (
        [ManualTestTypeEnum.MANUAL.value],
        [ManualTestTypeEnum.MANUAL.value, ManualTestTypeEnum.API.value],
        [ManualTestTypeEnum.MANUAL.value, ManualTestTypeEnum.UI.value],
    )

    def add_arguments(self, parser):
        parser.add_argument("--project-product-id", type=int, required=True, help="目标项目产品 ID")
        parser.add_argument("--owner-id", type=int, required=True, help="用例负责人 ID")
        parser.add_argument("--count", type=int, default=self.DEFAULT_COUNT, help="该 seed-key 的目标总数")
        parser.add_argument("--batch-size", type=int, default=self.DEFAULT_BATCH_SIZE, help="单批写入数量")
        parser.add_argument(
            "--module-ids",
            type=int,
            nargs="*",
            help="可选模块 ID 列表；不传时使用该项目产品下的全部叶子模块",
        )
        parser.add_argument(
            "--seed-key",
            default=self.DEFAULT_SEED_KEY,
            help="幂等批次标识，只允许小写字母、数字、下划线和中划线",
        )
        parser.add_argument("--apply", action="store_true", help="实际写入；不传时仅预检")

    @staticmethod
    def batched(values, size):
        iterator = iter(values)
        while batch := list(islice(iterator, size)):
            yield batch

    @classmethod
    def marker(cls, seed_key: str, index: int) -> str:
        return f"{seed_key}:{index:06d}"

    @classmethod
    def marker_index(cls, seed_key: str, value: str | None) -> int | None:
        prefix = f"{seed_key}:"
        if not value or not value.startswith(prefix):
            return None
        suffix = value[len(prefix):]
        return int(suffix) if suffix.isdigit() else None

    @classmethod
    def build_case(
            cls,
            *,
            index: int,
            case_sequence: int,
            seed_key: str,
            project_product_id: int,
            module_id: int,
            owner_id: int,
    ) -> ManualTestCase:
        category_one, category_two, category_three = cls.CATEGORY_PATHS[(index - 1) % len(cls.CATEGORY_PATHS)]
        scenario_type = (index - 1) % len(ApiCaseScenarioTypeEnum.get_key_list())
        scene_title = ApiCaseScenarioTypeEnum.obj()[scenario_type]
        return ManualTestCase(
            project_product_id=project_product_id,
            module_id=module_id,
            case_no=f"FT-{case_sequence:04d}",
            title=f"[DEV批量] {category_three}-{scene_title}-{index:06d}",
            category_level_1=category_one,
            category_level_2=category_two,
            category_level_3=category_three,
            priority=(index - 1) % len(CaseLevelEnum.get_key_list()),
            test_types=cls.TEST_TYPE_SETS[(index - 1) % len(cls.TEST_TYPE_SETS)],
            story_refs=[f"DEV-STORY-{((index - 1) % 500) + 1:04d}"],
            precondition="已准备 DEV 环境账号和基础业务数据。",
            test_point=f"验证{category_three}的{scene_title}处理逻辑",
            test_steps=[
                {"action": "进入目标功能并准备测试数据", "expected": "页面或接口正常加载"},
                {"action": f"执行第 {index:06d} 号批量测试场景", "expected": "系统按规则处理请求"},
                {"action": "检查响应、页面状态和数据结果", "expected": "结果与业务预期一致"},
            ],
            expected_result=f"{category_three}场景执行成功，数据状态正确。",
            acceptance_source="DEV 大数据量功能用例演示",
            status=FunctionalCaseStatusEnum.ENABLED.value,
            version_no=1,
            owner_id=owner_id,
            update_user_id=owner_id,
            automation_status="not_automated",
            change_status=ManualTestChangeStatusEnum.UNCHANGED.value,
            automation_impact_status=ManualTestAutomationImpactStatusEnum.NONE.value,
            scenario_layer=(index - 1) % len(ApiCaseScenarioLayerEnum.get_key_list()),
            scenario_type=scenario_type,
            scenario_tags=[cls.SCENARIO_TAGS[(index - 1) % len(cls.SCENARIO_TAGS)]],
            test_data=f"seed_index={index}; account=dev_user_{index % 1000:03d}",
            remark=f"由 seed_functional_test_cases 生成，批次：{seed_key}",
            source_block_id=cls.marker(seed_key, index),
            source_text="DEV 批量功能用例性能验证数据",
            source_hash=seed_key,
        )

    def validate_environment(self):
        current_env = getattr(settings, "DJANGO_ENV", None)
        database_name = str(connection.settings_dict.get("NAME") or "")
        if current_env != "dev":
            raise CommandError(f"命令只允许在 dev 环境执行，当前环境为 {current_env or 'unknown'}")
        if "dev" not in database_name.lower():
            raise CommandError(f"数据库名称未包含 dev，拒绝写入：{database_name}")
        return database_name

    def resolve_modules(self, project_product: ProjectProduct, module_ids: list[int] | None):
        queryset = ProductModule.objects.filter(project_product=project_product).annotate(
            child_count=Count("children"),
        ).filter(child_count=0)
        if module_ids:
            queryset = queryset.filter(id__in=module_ids)
        modules = list(queryset.order_by("id"))
        if not modules:
            raise CommandError("目标项目产品下没有可用的叶子模块")
        if module_ids and len(modules) != len(set(module_ids)):
            valid_ids = {item.id for item in modules}
            invalid_ids = sorted(set(module_ids) - valid_ids)
            raise CommandError(f"以下模块不存在、不属于目标项目产品或不是叶子模块：{invalid_ids}")
        return modules

    def next_case_sequence(self) -> int:
        maximum = 0
        for case_no in ManualTestCase.objects.filter(case_no__startswith="FT-").values_list("case_no", flat=True):
            match = self.CASE_NO_PATTERN.match(case_no or "")
            if match:
                maximum = max(maximum, int(match.group(1)))
        return maximum + 1

    def handle(self, *args, **options):
        database_name = self.validate_environment()
        count = options["count"]
        batch_size = options["batch_size"]
        seed_key = options["seed_key"]
        if count <= 0:
            raise CommandError("count 必须大于 0")
        if not 100 <= batch_size <= 10_000:
            raise CommandError("batch-size 必须在 100 到 10000 之间")
        if not self.SEED_KEY_PATTERN.fullmatch(seed_key):
            raise CommandError("seed-key 格式不正确")

        project_product = ProjectProduct.objects.filter(id=options["project_product_id"]).first()
        if not project_product:
            raise CommandError("目标项目产品不存在")
        owner = User.objects.filter(id=options["owner_id"]).first()
        if not owner:
            raise CommandError("用例负责人不存在")
        modules = self.resolve_modules(project_product, options.get("module_ids"))

        existing_markers = ManualTestCase.objects.filter(
            source_block_id__startswith=f"{seed_key}:",
        ).values_list("source_block_id", flat=True)
        existing_indexes = {
            parsed
            for value in existing_markers
            if (parsed := self.marker_index(seed_key, value)) is not None and 1 <= parsed <= count
        }
        missing_indexes = [index for index in range(1, count + 1) if index not in existing_indexes]
        self.stdout.write(
            str({
                "environment": "dev",
                "database": database_name,
                "project_product": f"{project_product.id}:{project_product.name}",
                "owner": f"{owner.id}:{owner.name}",
                "leaf_modules": len(modules),
                "target_count": count,
                "existing_count": len(existing_indexes),
                "pending_count": len(missing_indexes),
                "seed_key": seed_key,
            })
        )
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("仅预检，未写入数据；确认后增加 --apply"))
            return
        if not missing_indexes:
            self.stdout.write(self.style.SUCCESS("目标数据已完整存在，无需重复写入"))
            return

        next_sequence = self.next_case_sequence()
        inserted = 0
        for indexes in self.batched(missing_indexes, batch_size):
            rows = [
                self.build_case(
                    index=index,
                    case_sequence=next_sequence + inserted + offset,
                    seed_key=seed_key,
                    project_product_id=project_product.id,
                    module_id=modules[(index - 1) % len(modules)].id,
                    owner_id=owner.id,
                )
                for offset, index in enumerate(indexes)
            ]
            ManualTestCase.objects.bulk_create(rows, batch_size=batch_size)
            inserted += len(rows)
            self.stdout.write(f"已写入 {inserted}/{len(missing_indexes)} 条")

        final_count = ManualTestCase.objects.filter(
            source_block_id__startswith=f"{seed_key}:",
        ).count()
        self.stdout.write(self.style.SUCCESS(f"导入完成：本次新增 {inserted} 条，批次现有 {final_count} 条"))
