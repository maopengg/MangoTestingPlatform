# -*- coding: utf-8 -*-
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from src.apps.functional_test.models import FunctionalTestRequirement, ManualTestSuite
from src.apps.test_center.models import ProductModule


class Command(BaseCommand):
    help = "预检或回填三级模块树、功能测试需求主体和版本关系"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="实际写入数据；不传时仅预检",
        )

    @staticmethod
    def legacy_names(module: ProductModule) -> tuple[str, str]:
        return (
            (module.superior_module_1 or "").strip(),
            (module.superior_module_2 or "").strip(),
        )

    @classmethod
    def target_identity(cls, module: ProductModule) -> tuple:
        level_one, level_two = cls.legacy_names(module)
        if not level_one and not level_two:
            return module.project_product_id, None, module.name
        if level_one and not level_two:
            return module.project_product_id, level_one, module.name
        return module.project_product_id, level_one, level_two, module.name

    @classmethod
    def preflight(cls, modules: list[ProductModule]) -> dict:
        findings = []
        migrated_count = len([item for item in modules if item.level in (1, 2, 3)])
        if migrated_count == len(modules):
            module_map = {item.id: item for item in modules}
            for item in modules:
                parent = module_map.get(item.parent_id)
                if item.level == 1 and item.parent_id:
                    findings.append(f"一级模块 {item.id} 不应存在父节点")
                if item.level in (2, 3):
                    if not parent or parent.level != item.level - 1:
                        findings.append(f"模块 {item.id} 的父节点层级不连续")
                    elif parent.project_product_id != item.project_product_id:
                        findings.append(f"模块 {item.id} 与父节点属于不同项目产品")
            return {
                "passed": not findings,
                "findings": findings,
                "already_migrated": True,
                "module_count": len(modules),
                "required_root_count": 0,
                "required_level_two_count": 0,
                "new_parent_estimate": 0,
                "root_candidates": {},
                "level_two_candidates": {},
                "required_roots": set(),
                "required_level_two": set(),
            }
        if migrated_count:
            findings.append("模块层级处于部分迁移状态，请先核对后统一回滚或补齐，命令不会猜测处理")
        invalid = [item.id for item in modules if not cls.legacy_names(item)[0] and cls.legacy_names(item)[1]]
        if invalid:
            findings.append(f"存在只有二级旧路径的异常模块：{', '.join(map(str, invalid))}")

        identities = Counter(cls.target_identity(item) for item in modules)
        duplicates = [identity for identity, count in identities.items() if count > 1]
        if duplicates:
            findings.append(
                "迁移后同一父节点下存在重名模块："
                + "；".join(
                    " / ".join(str(part) for part in identity if part is not None) for identity in duplicates[:20])
            )

        root_candidates = {}
        level_two_candidates = {}
        for item in modules:
            level_one, level_two = cls.legacy_names(item)
            if not level_one and not level_two:
                key = (item.project_product_id, item.name)
                if key in root_candidates and root_candidates[key].id != item.id:
                    findings.append(f"一级模块候选重复：product={item.project_product_id}, name={item.name}")
                root_candidates[key] = item
            elif level_one and not level_two:
                key = (item.project_product_id, level_one, item.name)
                if key in level_two_candidates and level_two_candidates[key].id != item.id:
                    findings.append(
                        f"二级模块候选重复：product={item.project_product_id}, path={level_one}/{item.name}"
                    )
                level_two_candidates[key] = item

        required_roots = {
            (item.project_product_id, level_one)
            for item in modules
            for level_one, _ in [cls.legacy_names(item)]
            if level_one
        }
        required_level_two = {
            (item.project_product_id, level_one, level_two)
            for item in modules
            for level_one, level_two in [cls.legacy_names(item)]
            if level_one and level_two
        }
        return {
            "passed": not findings,
            "findings": findings,
            "module_count": len(modules),
            "required_root_count": len(required_roots),
            "required_level_two_count": len(required_level_two),
            "new_parent_estimate": len(required_roots - set(root_candidates))
                                   + len(required_level_two - set(level_two_candidates)),
            "root_candidates": root_candidates,
            "level_two_candidates": level_two_candidates,
            "required_roots": required_roots,
            "required_level_two": required_level_two,
        }

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        modules = list(ProductModule.objects.order_by("project_product_id", "id"))
        report = self.preflight(modules)
        summary = {
            "modules": report["module_count"],
            "new_parents": 0,
            "new_parent_estimate": report["new_parent_estimate"],
            "module_updates": 0,
            "suite_requirements": ManualTestSuite.objects.filter(requirement__isnull=True).count(),
        }
        if not report["passed"]:
            raise CommandError("模块树预检失败：" + "；".join(report["findings"]))
        if not apply_changes:
            self.stdout.write(self.style.WARNING("仅预检，未写入数据"))
            self.stdout.write(str(summary))
            return

        with transaction.atomic():
            if not report.get("already_migrated"):
                roots = dict(report["root_candidates"])
                for product_id, name in sorted(report["required_roots"]):
                    key = (product_id, name)
                    if key not in roots:
                        roots[key] = ProductModule.objects.create(
                            project_product_id=product_id,
                            parent=None,
                            name=name,
                            level=1,
                            sort=0,
                        )
                        summary["new_parents"] += 1

                level_two_nodes = dict(report["level_two_candidates"])
                for product_id, level_one_name, level_two_name in sorted(report["required_level_two"]):
                    key = (product_id, level_one_name, level_two_name)
                    if key not in level_two_nodes:
                        level_two_nodes[key] = ProductModule.objects.create(
                            project_product_id=product_id,
                            parent=roots[(product_id, level_one_name)],
                            name=level_two_name,
                            level=2,
                            sort=0,
                        )
                        summary["new_parents"] += 1

                for item in modules:
                    level_one_name, level_two_name = self.legacy_names(item)
                    if not level_one_name:
                        parent_id, level = None, 1
                    elif not level_two_name:
                        parent_id, level = roots[(item.project_product_id, level_one_name)].id, 2
                    else:
                        parent_id = level_two_nodes[
                            (item.project_product_id, level_one_name, level_two_name)
                        ].id
                        level = 3
                    if parent_id == item.id:
                        raise CommandError(f"模块 {item.id} 迁移后会成为自己的父节点")
                    ProductModule.objects.filter(id=item.id).update(parent_id=parent_id, level=level)
                    summary["module_updates"] += 1

            for suite in ManualTestSuite.objects.filter(requirement__isnull=True).select_related("owner"):
                requirement = FunctionalTestRequirement.objects.create(
                    name=suite.requirement_name or f"需求 {suite.id}",
                    project_product_id=suite.project_product_id,
                    owner_id=suite.owner_id,
                    update_user_id=suite.update_user_id,
                    status=suite.status,
                )
                suite.requirement = requirement
                suite.version_no = 1
                suite.save(update_fields=["requirement", "version_no"])

            remaining = ProductModule.objects.filter(level__isnull=True).count()
            if remaining:
                raise CommandError(f"迁移后仍有 {remaining} 个模块没有层级")

        self.stdout.write(self.style.SUCCESS("数据回填完成"))
        self.stdout.write(str(summary))
