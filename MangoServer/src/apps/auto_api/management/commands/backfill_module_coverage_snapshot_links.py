import hashlib

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count

from src.apps.auto_api.enums.module_coverage import (
    ModuleCoverageCaseStatus,
    ModuleCoverageInterfaceStatus,
)
from src.apps.auto_api.models import (
    ModuleCoverageCase,
    ModuleCoverageCaseSnapshot,
    ModuleCoverageInterfaceSnapshot,
    ModuleCoverageModuleInterface,
)
from src.apps.auto_api.services.module_coverage import ModuleCoverageService


class Command(BaseCommand):
    help = "审计或回填模块覆盖历史快照关系、链路状态、Case有效性和当前ApiInfo绑定"

    def add_arguments(self, parser):
        parser.add_argument("--only-missing-case-targets", action="store_true",
                            help="只补遗漏的Case覆盖目标，不改接口快照、ApiInfo绑定或资产修订")
        parser.add_argument("--project-product-id", type=int, help="限制遗漏目标修复的项目产品")
        parser.add_argument("--module-id", type=int, help="限制遗漏目标修复的模块")
        parser.add_argument(
            "--execute",
            action="store_true",
            help="实际写入；缺省只审计并回滚",
        )
        parser.add_argument(
            "--repair-duplicate-current",
            action="store_true",
            help="显式修复同一稳定接口身份存在多个当前快照的问题，保留最新扫描快照",
        )
        parser.add_argument(
            "--only-duplicate-current",
            action="store_true",
            help="只审计或修复重复当前快照，不执行其余历史全量重算",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        execute = options["execute"]
        repair_duplicate_current = options["repair_duplicate_current"]
        only_duplicate_current = options["only_duplicate_current"]
        if options["only_missing_case_targets"]:
            if repair_duplicate_current or only_duplicate_current:
                raise CommandError("遗漏目标修复不能与重复快照修复同时使用")
            result = ModuleCoverageService.backfill_missing_case_targets(
                project_product_id=options["project_product_id"], module_id=options["module_id"],
            )
            self.stdout.write(self.style.SUCCESS(
                f"遗漏目标检查{result['scanned']}条，关联{result['linked']}条，"
                f"未明确匹配{result['unresolved']}条；模式={'执行' if execute else '预览回滚'}"
            ))
            if not execute:
                transaction.set_rollback(True)
            return
        if options["project_product_id"] is not None or options["module_id"] is not None:
            raise CommandError("范围筛选仅用于 --only-missing-case-targets")
        if only_duplicate_current and not repair_duplicate_current:
            raise CommandError("--only-duplicate-current 必须与 --repair-duplicate-current 一起使用")
        linked = 0
        resolution_updated = 0
        binding_updated = 0
        case_validity_updated = 0
        module_interfaces_created = 0
        interface_snapshots_linked = 0
        cases_linked = 0
        legacy_case_snapshots_skipped = 0
        duplicate_current_repaired = 0
        conflicts: list[str] = []

        identity_fields = (
            "project_product_id", "module_id", "repository_key", "branch", "source_key_hash",
        )
        duplicate_groups = list(
            ModuleCoverageInterfaceSnapshot.objects.filter(is_current=True)
            .values(*identity_fields)
            .annotate(snapshot_count=Count("id"))
            .filter(snapshot_count__gt=1)
        )
        duplicate_identities = {
            tuple(group[field] for field in identity_fields) for group in duplicate_groups
        }
        if repair_duplicate_current:
            for group in duplicate_groups:
                candidates = list(
                    ModuleCoverageInterfaceSnapshot.objects.select_for_update().filter(
                        is_current=True,
                        **{field: group[field] for field in identity_fields},
                    ).order_by("-scan_id", "-id")
                )
                winner, losers = candidates[0], candidates[1:]
                if losers:
                    ModuleCoverageInterfaceSnapshot.objects.filter(
                        id__in=[item.id for item in losers],
                    ).update(is_current=False)
                    duplicate_current_repaired += len(losers)
                    self.stdout.write(
                        f"稳定接口身份保留快照#{winner.id}，取消旧当前快照："
                        f"{','.join(str(item.id) for item in losers)}"
                    )
            duplicate_identities.clear()
        else:
            if duplicate_identities:
                detail = "；".join(
                    f"稳定接口身份存在多个当前快照：{identity}"
                    for identity in sorted(duplicate_identities)[:20]
                )
                raise CommandError(
                    f"模块覆盖历史数据存在{len(duplicate_identities)}处冲突：{detail}"
                )

        if only_duplicate_current:
            self.stdout.write(self.style.SUCCESS(
                f"重复当前快照审计通过：发现{len(duplicate_groups)}组，"
                f"取消旧当前快照{duplicate_current_repaired}条；"
                f"模式={'执行' if execute else '只读回滚'}"
            ))
            if not execute:
                transaction.set_rollback(True)
            return

        for case_snapshot in ModuleCoverageCaseSnapshot.objects.filter(
                interface_snapshot__isnull=True,
        ).select_related("coverage_case", "scan"):
            source_key = str(
                (case_snapshot.payload or {}).get("interface_source_key")
                or case_snapshot.coverage_case.interface_source_key
                or ""
            ).strip()
            if not source_key:
                conflicts.append(f"Case快照#{case_snapshot.id}缺少interface_source_key")
                continue
            source_hash = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
            candidates = ModuleCoverageInterfaceSnapshot.objects.filter(
                scan_id=case_snapshot.scan_id,
                project_product_id=case_snapshot.coverage_case.project_product_id,
                module_id=case_snapshot.coverage_case.module_id,
                repository_key=case_snapshot.coverage_case.repository_key,
                branch=case_snapshot.coverage_case.branch,
                source_key_hash=source_hash,
                source_key=source_key,
            )
            candidate_count = candidates.count()
            if candidate_count == 0 and case_snapshot.scan.expected_interface_count == 0:
                legacy_case_snapshots_skipped += 1
                continue
            if candidate_count != 1:
                conflicts.append(
                    f"Case快照#{case_snapshot.id}匹配到{candidate_count}个接口快照"
                )
                continue
            case_snapshot.interface_snapshot = candidates.get()
            case_snapshot.save(update_fields=["interface_snapshot"])
            linked += 1

        current_interfaces: dict[
            tuple[int, int, str, str, str], ModuleCoverageInterfaceSnapshot
        ] = {}
        for interface in ModuleCoverageInterfaceSnapshot.objects.select_related(
                "scan", "api_info",
        ).order_by("id"):
            module_interface, created = ModuleCoverageModuleInterface.objects.get_or_create(
                project_product_id=interface.project_product_id,
                module_id=interface.module_id,
                repository_key=interface.repository_key,
                branch=interface.branch,
                source_key_hash=interface.source_key_hash,
                defaults={
                    "source_key": interface.source_key,
                    "first_seen_scan_id": interface.scan_id,
                    "last_seen_scan_id": interface.scan_id,
                },
            )
            if created:
                module_interfaces_created += 1
            relation_fields = []
            if module_interface.source_key != interface.source_key:
                module_interface.source_key = interface.source_key
                relation_fields.append("source_key")
            if interface.scan_id < module_interface.first_seen_scan_id:
                module_interface.first_seen_scan_id = interface.scan_id
                relation_fields.append("first_seen_scan")
            if interface.scan_id > module_interface.last_seen_scan_id:
                module_interface.last_seen_scan_id = interface.scan_id
                relation_fields.append("last_seen_scan")
            if relation_fields:
                module_interface.save(update_fields=[*relation_fields, "update_time"])
            if interface.module_interface_id != module_interface.id:
                interface.module_interface = module_interface
                interface.save(update_fields=["module_interface"])
                interface_snapshots_linked += 1

            resolution = ModuleCoverageService.interface_resolution(interface.mermaid, interface.node_ids)
            resolution_fields = []
            if interface.resolution_status != resolution["status"]:
                interface.resolution_status = resolution["status"]
                resolution_fields.append("resolution_status")
            if interface.resolution_reason != resolution["reason"]:
                interface.resolution_reason = resolution["reason"]
                resolution_fields.append("resolution_reason")
            if resolution_fields:
                interface.save(update_fields=resolution_fields)
                resolution_updated += 1

            if not interface.is_current:
                continue
            identity = (
                interface.project_product_id,
                interface.module_id,
                interface.repository_key,
                interface.branch,
                interface.source_key_hash,
            )
            if identity in duplicate_identities:
                continue
            if interface.lifecycle_status == ModuleCoverageInterfaceStatus.ACTIVE:
                current_interfaces[identity] = interface
                api_info, revision, status, reason = ModuleCoverageService.resolve_api_info_binding(
                    interface.scan,
                    interface.module_id,
                    {
                        "method": interface.method,
                        "url": interface.url,
                        "api_info_id": None,
                        "api_info_revision_id": None,
                    },
                    interface,
                )
                if (
                        interface.api_info_id != (api_info.id if api_info else None)
                        or interface.api_info_revision_id != (revision.id if revision else None)
                        or interface.api_info_binding_status != status
                        or interface.api_info_binding_reason != reason
                ):
                    interface.api_info = api_info
                    interface.api_info_revision = revision
                    interface.api_info_binding_status = status
                    interface.api_info_binding_reason = reason
                    interface.save(update_fields=[
                        "api_info", "api_info_revision",
                        "api_info_binding_status", "api_info_binding_reason",
                    ])
                    binding_updated += 1
            module_interface.api_info = interface.api_info
            module_interface.api_info_revision = interface.api_info_revision
            module_interface.api_info_binding_status = interface.api_info_binding_status
            module_interface.api_info_binding_reason = interface.api_info_binding_reason
            module_interface.current_snapshot = interface
            module_interface.last_seen_scan = interface.scan
            module_interface.lifecycle_status = interface.lifecycle_status
            module_interface.removed_at = interface.removed_at
            module_interface.save(update_fields=[
                "api_info", "api_info_revision", "api_info_binding_status",
                "api_info_binding_reason", "current_snapshot", "last_seen_scan",
                "lifecycle_status", "removed_at", "update_time",
            ])

        for coverage_case in ModuleCoverageCase.objects.filter(
                removed_at__isnull=True,
        ).exclude(status=ModuleCoverageCaseStatus.REMOVED).select_related(
            "current_snapshot",
            "current_snapshot__interface_snapshot",
            "current_snapshot__interface_snapshot__module_interface",
        ):
            identity = (
                coverage_case.project_product_id,
                coverage_case.module_id,
                coverage_case.repository_key,
                coverage_case.branch,
                coverage_case.interface_source_key_hash,
            )
            current_interface = current_interfaces.get(identity)
            if current_interface and (
                    coverage_case.module_interface_id != current_interface.module_interface_id
                    or coverage_case.module_id != current_interface.module_id
            ):
                coverage_case.module_interface_id = current_interface.module_interface_id
                coverage_case.module_id = current_interface.module_id
                coverage_case.save(update_fields=["module_interface", "module", "update_time"])
                cases_linked += 1
            assessment = ModuleCoverageService.case_coverage_assessment(
                coverage_case,
                current_interface,
            )
            if (
                    coverage_case.coverage_validity != assessment["status"]
                    or coverage_case.coverage_validity_reason != assessment["reason"]
            ):
                coverage_case.coverage_validity = assessment["status"]
                coverage_case.coverage_validity_reason = assessment["reason"]
                coverage_case.save(update_fields=[
                    "coverage_validity",
                    "coverage_validity_reason",
                    "update_time",
                ])
                case_validity_updated += 1

        if conflicts:
            transaction.set_rollback(True)
            detail = "；".join(conflicts[:20])
            raise CommandError(f"模块覆盖历史数据存在{len(conflicts)}处冲突：{detail}")

        self.stdout.write(self.style.SUCCESS(
            f"审计通过：Case快照关系{linked}条，链路状态{resolution_updated}条，"
            f"Case有效性{case_validity_updated}条，ApiInfo绑定{binding_updated}条，"
            f"模块接口关系新建{module_interfaces_created}条，接口快照关联{interface_snapshots_linked}条，"
            f"Case关联{cases_linked}条，旧版无接口快照保留{legacy_case_snapshots_skipped}条，"
            f"重复当前快照修复{duplicate_current_repaired}条；"
            f"模式={'执行' if execute else '只读回滚'}"
        ))
        if not execute:
            transaction.set_rollback(True)
