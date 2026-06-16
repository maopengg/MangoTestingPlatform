# -*- coding: utf-8 -*-
import json

from src.apps.ai.models import AiAgentContext
from src.apps.functional_test.service.common import FunctionalTestContextResourceService, _hash_text, enum_label
from src.apps.functional_test.service.case_sync import FunctionalTestCaseSyncService
from src.common.enums.ai_enum import AiAgentTaskStatusEnum
from src.common.enums.manual_test_enum import FunctionalTestContextKeyEnum


class AgentContextService:
    @classmethod
    def build_functional_suite_context(cls, suite, context_keys: list | None = None) -> dict:
        payload = FunctionalTestCaseSyncService.build_context_payload(suite, context_keys)
        suite_context = FunctionalTestContextResourceService.render_suite_context(suite, payload["context_keys"])
        if FunctionalTestContextKeyEnum.PLATFORM_CASE.value in payload["context_keys"]:
            suite_context[FunctionalTestContextKeyEnum.PLATFORM_CASE.value] = FunctionalTestCaseSyncService.render_platform_cases(suite)
        previous = cls.latest_success_context(suite.id, "manual_case_sync_dialog", payload["context_hash"])
        history = cls.context_history(suite.id, "manual_case_sync_dialog", payload["context_hash"], limit=5)
        context_summary = cls.build_context_summary_from_text_map(suite_context, payload["context_keys"])
        history_summary = cls.history_summary(history)
        reuse_context = previous is not None
        payload.update(
            {
                "context_summary": context_summary,
                "history_summary": history_summary,
                "ai_source_content": payload["raw_case_context"]
                if not reuse_context
                else f"本次为同一需求下相同上下文的连续追问，不重复发送完整文件。\n上下文摘要：\n{context_summary}\n\n历史对话：\n{history_summary}",
                "reuse_context": reuse_context,
                "reuse_context_id": previous.id if previous else None,
            }
        )
        return payload

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
    def build_context_summary_from_text_map(suite_context: dict, context_keys: list[int], limit_per_context: int = 800) -> str:
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
