# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 产品模块三级树结构升级
# @Time   : 2026-07-17 00:00
# @Author : Codex
from django.db import transaction

from src.apps.functional_test.management.commands.migrate_functional_test_hierarchy import (
    Command as ModuleHierarchyMigration,
)
from src.apps.test_center.models import ProductModule


def _upgrade_module_hierarchy(modules: list[ProductModule], report: dict) -> dict:
    stats = {
        "module_count": len(modules),
        "created_level_one_count": 0,
        "created_level_two_count": 0,
        "updated_module_count": 0,
        "already_migrated": bool(report.get("already_migrated")),
    }
    if report.get("already_migrated"):
        return stats

    roots = dict(report["root_candidates"])
    for project_product_id, name in sorted(report["required_roots"]):
        key = (project_product_id, name)
        if key in roots:
            continue
        roots[key] = ProductModule.objects.create(
            project_product_id=project_product_id,
            parent=None,
            name=name,
            level=1,
            sort=0,
        )
        stats["created_level_one_count"] += 1

    level_two_nodes = dict(report["level_two_candidates"])
    for project_product_id, level_one_name, level_two_name in sorted(
        report["required_level_two"]
    ):
        key = (project_product_id, level_one_name, level_two_name)
        if key in level_two_nodes:
            continue
        level_two_nodes[key] = ProductModule.objects.create(
            project_product_id=project_product_id,
            parent=roots[(project_product_id, level_one_name)],
            name=level_two_name,
            level=2,
            sort=0,
        )
        stats["created_level_two_count"] += 1

    for module in modules:
        level_one_name, level_two_name = ModuleHierarchyMigration.legacy_names(module)
        if not level_one_name:
            parent_id, level = None, 1
        elif not level_two_name:
            parent_id = roots[(module.project_product_id, level_one_name)].id
            level = 2
        else:
            parent_id = level_two_nodes[
                (module.project_product_id, level_one_name, level_two_name)
            ].id
            level = 3
        if parent_id == module.id:
            raise RuntimeError(f"模块 {module.id} 迁移后会成为自己的父节点")
        ProductModule.objects.filter(id=module.id).update(
            parent_id=parent_id,
            level=level,
        )
        stats["updated_module_count"] += 1
    return stats


def main_7_0_3() -> dict:
    print("开始执行产品模块三级树结构升级 7.0.3...")
    print("-" * 50)
    with transaction.atomic():
        modules = list(
            ProductModule.objects.select_for_update().order_by(
                "project_product_id",
                "id",
            )
        )
        report = ModuleHierarchyMigration.preflight(modules)
        if not report["passed"]:
            raise RuntimeError("模块树升级预检失败：" + "；".join(report["findings"]))

        stats = _upgrade_module_hierarchy(modules, report)
        remaining_count = ProductModule.objects.filter(level__isnull=True).count()
        if remaining_count:
            raise RuntimeError(f"模块树升级后仍有 {remaining_count} 个模块没有层级")

    if stats["already_migrated"]:
        print(f"现有 {stats['module_count']} 个模块已经完成树结构升级，本次无需写入。")
    else:
        print(
            "模块树升级完成："
            f"原模块 {stats['module_count']} 个，"
            f"新增一级模块 {stats['created_level_one_count']} 个，"
            f"新增二级模块 {stats['created_level_two_count']} 个，"
            f"回填模块 {stats['updated_module_count']} 个。"
        )
    print("旧字段 superior_module_1/superior_module_2 已保留，仅用于迁移核对。")
    return stats
