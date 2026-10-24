# -*- coding: utf-8 -*-
import json

from src.apps.ai.enums import AiAgentTaskStatusEnum
from src.apps.ai.exceptions import ai_service_error
from src.apps.ai.models import AiAgentArtifact, AiAgentContext
from src.apps.functional_test.enums import FunctionalTestContextKeyEnum
from src.apps.functional_test.selectors.querysets import FunctionalTestQuerySelector
from src.apps.functional_test.services.case_sync import FunctionalTestCaseSyncService
from src.apps.functional_test.services.common import FunctionalTestContextResourceService, _hash_text, enum_label
from src.apps.functional_test.services.suite import ManualTestSuiteService


class AgentContextService:
    @staticmethod
    def module_path(module) -> str:
        names = []
        current = module
        while current:
            names.append(current.name)
            current = current.parent
        return " / ".join(reversed(names))

    @staticmethod
    def resource_manifest(resources, source: str) -> list[dict]:
        return [
            {
                "resource_id": resource.id,
                "suite_id": resource.suite_id,
                "context_key": resource.context_key,
                "title": resource.title,
                "content_type": resource.content_type,
                "text_hash": _hash_text(
                    FunctionalTestContextResourceService.render_resource(resource)
                ),
                "source": source,
            }
            for resource in resources
        ]

    @classmethod
    def build_functional_suite_context(
            cls,
            suite,
            context_keys: list | None = None,
            historical_context: list | None = None,
            current_resource_ids: list | None = None,
    ) -> dict:
        payload = FunctionalTestCaseSyncService.build_context_payload(suite, context_keys)
        resource_selection_provided = current_resource_ids is not None
        if resource_selection_provided:
            requested_ids = {int(item) for item in current_resource_ids or []}
            selectable_keys = [
                key
                for key in payload["context_keys"]
                if key != FunctionalTestContextKeyEnum.PLATFORM_CASE.value
            ]
            resources = list(FunctionalTestQuerySelector.functional_test_context_resource().filter(
                id__in=requested_ids,
                suite=suite,
                enabled=True,
                context_key__in=selectable_keys,
            ).order_by("context_key", "id"))
            if {item.id for item in resources} != requested_ids:
                raise ai_service_error("当前上下文资料不存在、已停用或不属于当前需求")
            rendered = {}
            for resource in resources:
                rendered.setdefault(resource.context_key, []).append(
                    FunctionalTestContextResourceService.render_resource(resource)
                )
            selected_sections = []
            for key, parts in rendered.items():
                selected_sections.append(
                    f"{enum_label(FunctionalTestContextKeyEnum, key)}：\n" + "\n\n".join(parts)
                )
            if FunctionalTestContextKeyEnum.PLATFORM_CASE.value in payload["context_keys"]:
                selected_sections.append(
                    f"{enum_label(FunctionalTestContextKeyEnum, FunctionalTestContextKeyEnum.PLATFORM_CASE.value)}：\n"
                    + FunctionalTestCaseSyncService.render_platform_cases(suite)
                )
            selected_text = "\n\n".join(selected_sections)
            payload["selected_context"] = selected_text
            payload["context_text"] = selected_text
        selected_resource_keys = [
            key
            for key in payload["context_keys"]
            if key != FunctionalTestContextKeyEnum.PLATFORM_CASE.value
        ]
        current_resources = list(
            FunctionalTestQuerySelector.functional_test_context_resource().filter(
                suite=suite,
                enabled=True,
                context_key__in=selected_resource_keys,
                **({"id__in": current_resource_ids or []} if resource_selection_provided else {}),
            ).order_by("context_key", "id")
        )
        if resource_selection_provided:
            suite_context = {key: "" for key in payload["context_keys"]}
            for resource in current_resources:
                rendered = FunctionalTestContextResourceService.render_resource(resource)
                existing = suite_context.get(resource.context_key) or ""
                suite_context[resource.context_key] = "\n\n".join(
                    part for part in [existing, rendered] if part
                )
        else:
            suite_context = FunctionalTestContextResourceService.render_suite_context(
                suite,
                payload["context_keys"],
            )
        platform_case_inventory = FunctionalTestCaseSyncService.render_platform_case_inventory(suite)
        platform_case_text = ""
        if FunctionalTestContextKeyEnum.PLATFORM_CASE.value in payload["context_keys"]:
            platform_case_text = FunctionalTestCaseSyncService.render_platform_cases(suite)
            suite_context[FunctionalTestContextKeyEnum.PLATFORM_CASE.value] = platform_case_text
        historical_text, historical_manifest = cls.compile_historical_context(suite, historical_context or [])
        if historical_text:
            payload["context_text"] = "\n\n".join(
                part for part in [payload.get("context_text") or "", historical_text] if part
            )
        source_manifest = {
            "suite_id": suite.id,
            "requirement_id": suite.requirement_id,
            "version_no": suite.version_no,
            "requirement_name": suite.requirement_name or "",
            "iteration": suite.iteration or "",
            "owner_id": suite.owner_id,
            "project_product_id": suite.project_product_id,
            "module_id": suite.module_id,
            "module_level": suite.module.level if suite.module_id else None,
            "module_path": cls.module_path(suite.module) if suite.module_id else "",
            "resources": cls.resource_manifest(current_resources, "current"),
            "platform_case_snapshot": {
                "inventory_included": bool(platform_case_inventory),
                "full_snapshot_included": bool(platform_case_text),
                "case_count": suite.manualtestcase_set.count(),
                "inventory_hash": _hash_text(platform_case_inventory) if platform_case_inventory else "",
                "full_snapshot_hash": _hash_text(platform_case_text) if platform_case_text else "",
                "source": "current",
            },
            "historical_context": historical_manifest,
        }
        payload["context_hash"] = _hash_text(
            json.dumps(
                {
                    "suite_id": suite.id,
                    "source_manifest": source_manifest,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        previous = cls.latest_success_context(suite.id, "manual_case_sync_dialog", payload["context_hash"])
        history = cls.context_history(suite.id, "manual_case_sync_dialog", payload["context_hash"], limit=5)
        context_summary = cls.build_context_summary_from_text_map(suite_context, payload["context_keys"])
        history_summary = cls.history_summary(history)
        reuse_context = previous is not None
        reusable_artifacts = cls.reusable_functional_artifacts(previous)
        reusable_artifact_text = (
            json.dumps(reusable_artifacts, ensure_ascii=False, default=str)[:60000]
            if reusable_artifacts
            else ""
        )
        source_content = payload.get("context_text") or payload.get("raw_case_context") or payload.get(
            "selected_context") or ""
        payload.update(
            {
                "context_summary": context_summary,
                "history_summary": history_summary,
                "ai_source_content": source_content
                if not reuse_context
                else "\n\n".join(
                    part
                    for part in [
                        "本次为同一需求下相同上下文的连续追问，不重复发送完整文件。",
                        f"上下文摘要：\n{context_summary}" if context_summary else "",
                        f"上一成功任务的已验证结构化产物：\n{reusable_artifact_text}"
                        if reusable_artifact_text
                        else "",
                        f"历史对话：\n{history_summary}" if history_summary else "",
                    ]
                    if part
                ),
                "reuse_context": reuse_context,
                "reuse_context_id": previous.id if previous else None,
                "reusable_artifacts": reusable_artifacts,
                "historical_context_manifest": historical_manifest,
                "current_resource_ids": [resource.id for resource in current_resources],
                "source_manifest": source_manifest,
                "existing_case_inventory": platform_case_inventory,
            }
        )
        return payload

    @staticmethod
    def reusable_functional_artifacts(previous: AiAgentContext | None) -> dict:
        if not previous or not previous.task_id:
            return {}
        reusable_types = {
            "understand_requirement",
            "inventory_existing_cases",
            "analyze_coverage",
            "plan_cases",
        }
        artifacts = AiAgentArtifact.objects.filter(
            task_id=previous.task_id,
            artifact_type__in=reusable_types,
            status__in=["validated", "committed"],
        ).order_by("id")
        result = {}
        for artifact in artifacts:
            result[artifact.artifact_type] = artifact.content_json
        return result

    @classmethod
    def compile_historical_context(cls, current_suite, references: list[dict]) -> tuple[str, list[dict]]:
        sections = []
        manifest = []
        module_scope_ids = set(ManualTestSuiteService.module_scope_ids(current_suite.module_id))
        for reference in references:
            try:
                suite_id = int(reference.get("suite_id"))
            except (TypeError, ValueError, AttributeError):
                raise ai_service_error("历史上下文缺少有效的需求版本 ID")
            historical_suite = FunctionalTestQuerySelector.manual_test_suite().select_related(
                "module",
                "module__parent",
                "module__parent__parent",
            ).filter(
                id=suite_id,
                project_product_id=current_suite.project_product_id,
            ).first()
            if not historical_suite or historical_suite.id == current_suite.id:
                raise ai_service_error("历史上下文需求版本不存在、属于其他项目产品或不是历史版本")
            same_requirement = bool(
                current_suite.requirement_id
                and historical_suite.requirement_id == current_suite.requirement_id
            )
            same_module_scope = bool(
                historical_suite.module_id
                and historical_suite.module_id in module_scope_ids
            )
            if not same_requirement and not same_module_scope:
                raise ai_service_error("历史上下文只能选择同一需求版本或当前模块范围内的需求")
            resource_ids = []
            for value in reference.get("resource_ids") or []:
                try:
                    resource_ids.append(int(value))
                except (TypeError, ValueError):
                    raise ai_service_error("历史上下文包含无效的资料 ID")
            resources = list(
                FunctionalTestQuerySelector.functional_test_context_resource().filter(
                    suite=historical_suite,
                    id__in=resource_ids,
                    enabled=True,
                ).order_by("context_key", "id")
            )
            if set(resource_ids) != {resource.id for resource in resources}:
                raise ai_service_error("历史上下文资料不存在、已停用或不属于所选历史需求")
            resource_text = "\n\n".join(
                FunctionalTestContextResourceService.render_resource(resource)
                for resource in resources
            )
            include_case_snapshot = bool(reference.get("include_case_snapshot"))
            case_text = (
                FunctionalTestCaseSyncService.render_platform_cases(historical_suite)
                if include_case_snapshot
                else ""
            )
            body = "\n\n".join(part for part in [resource_text, case_text] if part)
            if not body:
                continue
            sections.append(
                "\n".join(
                    [
                        "[历史参考，不得覆盖当前版本事实]",
                        f"suite_id：{historical_suite.id}",
                        f"需求：{historical_suite.requirement_name or ''}",
                        f"版本：{historical_suite.version_no or '-'}",
                        body,
                    ]
                )
            )
            manifest.append(
                {
                    "suite_id": historical_suite.id,
                    "requirement_id": historical_suite.requirement_id,
                    "version_no": historical_suite.version_no,
                    "module_id": historical_suite.module_id,
                    "module_level": historical_suite.module.level if historical_suite.module_id else None,
                    "module_path": cls.module_path(historical_suite.module) if historical_suite.module_id else "",
                    "resources": cls.resource_manifest(resources, "historical_reference"),
                    "resource_ids": [resource.id for resource in resources],
                    "include_case_snapshot": include_case_snapshot,
                    "case_snapshot": {
                        "included": include_case_snapshot,
                        "case_count": historical_suite.manualtestcase_set.count() if include_case_snapshot else 0,
                        "text_hash": _hash_text(case_text) if case_text else "",
                        "source": "historical_reference",
                    },
                    "source": "historical_reference",
                }
            )
        return "\n\n".join(sections), manifest

    @classmethod
    def normalize_api_context_keys(cls, context_keys: list | None) -> list:
        default_keys = [
            FunctionalTestContextKeyEnum.REQUIREMENT_DOC.value,
            FunctionalTestContextKeyEnum.DEVELOPMENT_DESIGN.value,
            FunctionalTestContextKeyEnum.API_DOC.value,
            FunctionalTestContextKeyEnum.DEVELOPMENT_CODE.value,
            FunctionalTestContextKeyEnum.SQL_QUERY.value,
        ]
        return FunctionalTestCaseSyncService.normalize_context_keys(context_keys) if context_keys else default_keys

    @staticmethod
    def build_context_text(suite_context: dict, context_keys: list[int]) -> str:
        parts = []
        for key in context_keys:
            content = suite_context.get(key) or ""
            if content:
                parts.append(f"{enum_label(FunctionalTestContextKeyEnum, key)}：\n{content}")
        return "\n\n".join(parts)

    @staticmethod
    def build_context_summary(suite_context: dict, context_keys: list[int], limit_per_context: int = 800) -> str:
        parts = []
        for key in context_keys:
            content = (suite_context.get(key) or "").strip()
            if content:
                parts.append(f"{enum_label(FunctionalTestContextKeyEnum, key)}摘要：\n{content[:limit_per_context]}")
        return "\n\n".join(parts)

    @classmethod
    def build_api_context_package(cls, suite, context_keys: list | None = None) -> dict:
        selected_keys = cls.normalize_api_context_keys(context_keys)
        suite_context = FunctionalTestContextResourceService.render_suite_context(suite, selected_keys)
        context_text = cls.build_context_text(suite_context, selected_keys)
        context_hash = _hash_text(
            json.dumps(
                {
                    "suite_id": suite.id,
                    "requirement_id": suite.requirement_id,
                    "version_no": suite.version_no,
                    "requirement_name": suite.requirement_name or "",
                    "iteration": suite.iteration or "",
                    "owner_id": suite.owner_id,
                    "project_product_id": suite.project_product_id,
                    "module_id": suite.module_id,
                    "context_keys": selected_keys,
                    "context_text": context_text,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        previous = cls.latest_success_context(
            suite.id,
            "api_case_plan",
            context_hash,
        )
        history = cls.context_history(
            suite.id,
            context_type="api_case_plan",
            context_hash=context_hash,
            limit=5,
        )
        return {
            "context_keys": selected_keys,
            "context_hash": context_hash,
            "context_text": context_text,
            "context_summary": cls.build_context_summary(suite_context, selected_keys),
            "reuse_context": previous is not None,
            "reuse_context_id": previous.id if previous else None,
            "history": [
                {
                    "id": item.id,
                    "case_id": item.manual_case_id,
                    "case_title": (item.result_snapshot or {}).get("case_title") or "",
                    "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "summary": item.summary,
                }
                for item in history
            ],
        }

    @staticmethod
    def latest_success_context(suite_id: int, context_type: str, context_hash: str):
        return (
            AiAgentContext.objects.filter(
                suite_id=suite_id,
                context_type=context_type,
                context_hash=context_hash,
                result_snapshot__status=AiAgentTaskStatusEnum.SUCCESS.value,
            )
            .order_by("-id")
            .first()
        )

    @staticmethod
    def context_history(suite_id: int, context_type: str, context_hash: str | None = None, limit: int = 5):
        queryset = AiAgentContext.objects.filter(suite_id=suite_id, context_type=context_type)
        if context_hash:
            queryset = queryset.filter(context_hash=context_hash)
        return list(queryset.order_by("-id")[:limit])

    @staticmethod
    def history_summary(history: list[AiAgentContext]) -> str:
        return "\n".join(
            [
                f"- {item.create_time.strftime('%Y-%m-%d %H:%M:%S')}：{item.summary or ''}"
                for item in history
            ]
        )

    @staticmethod
    def build_context_summary_from_text_map(suite_context: dict, context_keys: list[int],
                                            limit_per_context: int = 800) -> str:
        parts = []
        for key in context_keys:
            content = (suite_context.get(key) or "").strip()
            if content:
                parts.append(f"{enum_label(FunctionalTestContextKeyEnum, key)}摘要：\n{content[:limit_per_context]}")
        return "\n\n".join(parts)

    @staticmethod
    def save_context(
            suite_id: int,
            context_type: str,
            context_hash: str,
            source_snapshot: dict,
            result_snapshot: dict,
            summary: str = "",
            task=None,
            manual_case_id: int | None = None,
            skill_snapshot: dict | None = None,
            mcp_snapshot: dict | None = None,
            user_instruction: str = "",
            user_id: int | None = None,
    ) -> AiAgentContext:
        return AiAgentContext.objects.create(
            suite_id=suite_id,
            manual_case_id=manual_case_id,
            context_type=context_type,
            context_hash=context_hash,
            source_snapshot=source_snapshot or {},
            result_snapshot=result_snapshot or {},
            summary=(summary or "")[:60000],
            task=task,
            skill_snapshot=skill_snapshot or {},
            mcp_snapshot=mcp_snapshot or {},
            user_instruction=user_instruction or "",
            create_user_id=user_id,
        )
