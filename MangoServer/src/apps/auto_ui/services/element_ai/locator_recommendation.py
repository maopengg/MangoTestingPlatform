# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import re
import uuid

from django.core.cache import cache

from src.apps.system.services.ai.client import AiService as AgentModelGateway
from src.apps.system.services.ai.json_output import extract_ai_json
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_AI_LOCATOR_CONTEXT_INVALID,
    UI_AI_LOCATOR_RECOMMEND_FAILED,
    UI_AI_LOCATOR_SESSION_EXPIRED,
)
from src.common.prompts import get_prompt
from .data_sanitizer import ElementAiDataSanitizer

logger = logging.getLogger(__name__)


class ElementAiLocatorRecommendationService:
    """Generate safe locator batches; browser validation remains executor-owned."""

    CACHE_PREFIX = "ui:element:ai-locator:"
    CACHE_TTL_SECONDS = 600
    BATCH_SIZE = 5
    MODEL_ATTEMPTS = 2
    ALLOWED_STRATEGIES = {
        "role",
        "label",
        "placeholder",
        "text",
        "testid",
        "title",
        "alt_text",
        "css",
        "xpath",
    }

    @classmethod
    def recommend(cls, data: dict, user_id: int | None = None) -> dict:
        snapshot_id = str(data.get("snapshot_id") or "").strip()
        if snapshot_id:
            session = cache.get(cls._cache_key(snapshot_id))
            if not session or session.get("user_id") != user_id:
                raise AutoUiError(UI_AI_LOCATOR_SESSION_EXPIRED)
            if "location_description" in data or "surrounding_text" in data:
                session["user_guidance"] = cls._sanitize_user_guidance(data)
        else:
            context = cls._sanitize_context(data.get("context") or {})
            if not cls._has_target_context(context):
                raise AutoUiError(UI_AI_LOCATOR_CONTEXT_INVALID)
            snapshot_id = uuid.uuid4().hex
            session = {
                "user_id": user_id,
                "context": context,
                "existing_locators": ElementAiDataSanitizer.locator_candidates(
                    data.get("existing_locators") or []
                )[:10],
                "candidates": [],
                "batch": 0,
                "user_guidance": cls._sanitize_user_guidance(data),
            }

        try:
            ai_result = cls._request_candidates(session)
        except AutoUiError:
            raise
        except Exception as error:
            logger.exception(
                "AI locator recommendation request failed error_type=%s",
                type(error).__name__,
            )
            raise AutoUiError(UI_AI_LOCATOR_RECOMMEND_FAILED, value=(str(error),), error=str(error))

        raw_candidates = ai_result["candidates"]
        ai_reason = ai_result["reason"]
        excluded = {
            cls._candidate_identity(item)
            for item in (session.get("existing_locators") or []) + (session.get("candidates") or [])
        }
        candidates = []
        invalid_count = 0
        duplicate_count = 0
        for item in raw_candidates:
            candidate = cls._normalize_candidate(item)
            if not candidate:
                invalid_count += 1
                continue
            identity = cls._candidate_identity(candidate)
            if identity in excluded:
                duplicate_count += 1
                continue
            excluded.add(identity)
            candidates.append(candidate)
            if len(candidates) >= cls.BATCH_SIZE:
                break

        session["batch"] = int(session.get("batch") or 0) + 1
        session["candidates"] = (session.get("candidates") or []) + candidates
        cache.set(cls._cache_key(snapshot_id), session, cls.CACHE_TTL_SECONDS)
        diagnostics = cls._build_diagnostics(
            generated_count=len(raw_candidates),
            available_count=len(candidates),
            invalid_count=invalid_count,
            duplicate_count=duplicate_count,
            ai_reason=ai_reason,
            model_attempts=ai_result.get("model_attempts") or 1,
        )
        logger.info(
            "AI locator recommendation batch=%s generated=%s available=%s invalid=%s "
            "duplicate=%s model_attempts=%s",
            session["batch"],
            diagnostics["generated_count"],
            diagnostics["available_count"],
            diagnostics["invalid_count"],
            diagnostics["duplicate_count"],
            diagnostics["model_attempts"],
        )
        return {
            "snapshot_id": snapshot_id,
            "batch": session["batch"],
            "candidates": candidates,
            "has_more": bool(candidates),
            "expires_in": cls.CACHE_TTL_SECONDS,
            "diagnostics": diagnostics,
        }

    @classmethod
    def _request_candidates(cls, session: dict) -> dict:
        prompt = get_prompt("ui.locator_recommendation")
        context = session.get("context") or {}
        used = (session.get("existing_locators") or []) + (session.get("candidates") or [])
        prompt_payload = {
            "task": prompt.values["task"],
            "batch": int(session.get("batch") or 0) + 1,
            "target_context": context,
            "user_guidance": session.get("user_guidance") or {},
            "excluded_locators": [
                {"exp": item.get("exp"), "loc": item.get("loc")}
                for item in used[-20:]
            ],
            "output_contract": prompt.values["output_contract"],
            "rules": prompt.values["rules"],
        }
        messages = [
            {
                "role": "system",
                "content": prompt.system,
            },
            {
                "role": "user",
                "content": json.dumps(prompt_payload, ensure_ascii=False),
            },
        ]
        last_reason = ""
        for attempt in range(1, cls.MODEL_ATTEMPTS + 1):
            response = AgentModelGateway.json_chat(
                messages=messages,
                temperature=0.25,
                max_tokens=5000,
                thinking={"type": "disabled"},
            )
            payload = extract_ai_json(response)
            candidates = cls._extract_candidate_rows(payload)
            ai_reason = cls._extract_ai_reason(payload)
            metadata = cls._response_metadata(response)
            if candidates or ai_reason:
                logger.info(
                    "AI locator model response accepted attempt=%s/%s candidates=%s "
                    "has_reason=%s metadata=%s",
                    attempt,
                    cls.MODEL_ATTEMPTS,
                    len(candidates),
                    bool(ai_reason),
                    metadata,
                )
                return {
                    "candidates": candidates,
                    "reason": ai_reason,
                    "model_attempts": attempt,
                }

            last_reason = cls._empty_response_reason(response, payload)
            logger.warning(
                "AI locator model response unusable attempt=%s/%s reason=%s metadata=%s",
                attempt,
                cls.MODEL_ATTEMPTS,
                last_reason,
                metadata,
            )
            if attempt < cls.MODEL_ATTEMPTS:
                messages = messages + [{
                    "role": "user",
                    "content": prompt.template("retry"),
                }]

        return {
            "candidates": [],
            "reason": f"{last_reason}（已自动重试 1 次，仍未获得定位器候选）",
            "model_attempts": cls.MODEL_ATTEMPTS,
        }

    @staticmethod
    def _response_metadata(response) -> dict:
        """Return safe diagnostics only; never log model content or element context."""
        metadata = {
            "response_type": type(response).__name__,
            "choices_count": 0,
            "finish_reason": None,
            "content_type": None,
            "content_length": 0,
            "reasoning_content_present": False,
            "reasoning_content_length": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "model": None,
            "response_id_present": False,
        }
        if not isinstance(response, dict):
            return metadata
        metadata["model"] = ElementAiDataSanitizer.text(response.get("model"), 120) or None
        metadata["response_id_present"] = bool(response.get("id"))
        choices = response.get("choices")
        if isinstance(choices, list):
            metadata["choices_count"] = len(choices)
        first_choice = choices[0] if isinstance(choices, list) and choices else {}
        if not isinstance(first_choice, dict):
            return metadata
        metadata["finish_reason"] = ElementAiDataSanitizer.text(
            first_choice.get("finish_reason"), 80
        ) or None
        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            metadata["content_type"] = type(content).__name__
            if isinstance(content, str):
                metadata["content_length"] = len(content)
            elif isinstance(content, (dict, list)):
                metadata["content_length"] = len(content)
            reasoning_content = message.get("reasoning_content")
            metadata["reasoning_content_present"] = reasoning_content not in (
                None,
                "",
                {},
                [],
            )
            if isinstance(reasoning_content, str):
                metadata["reasoning_content_length"] = len(reasoning_content)
        usage = response.get("usage")
        if isinstance(usage, dict):
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                value = usage.get(key)
                metadata[key] = value if isinstance(value, int) else None
        return metadata

    @staticmethod
    def _empty_response_reason(response, payload) -> str:
        """Describe contract violations without exposing the model's raw response."""
        if not isinstance(response, dict):
            return "AI 服务返回的数据结构无效，未提供候选定位器"
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            return "AI 服务未返回可用的 choices，无法提取定位器候选"
        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get("message") if isinstance(first_choice, dict) else None
        if not isinstance(message, dict):
            return "AI 服务返回项缺少 message，无法提取定位器候选"
        content = message.get("content")
        if content in (None, "", {}):
            finish_reason = first_choice.get("finish_reason")
            if finish_reason == "length":
                if message.get("reasoning_content") not in (None, "", {}, []):
                    return "AI 推理过程耗尽输出 token，最终 JSON 被截断，未生成定位器候选"
                return "AI 输出达到 token 上限且最终内容为空，未生成定位器候选"
            if finish_reason == "content_filter":
                return "AI 输出被内容策略中止，未生成定位器候选"
            if message.get("reasoning_content") not in (None, "", {}, []):
                return "AI 仅返回了推理内容，未返回最终 JSON 结果，无法生成定位器候选"
            return "AI 服务返回内容为空，未生成定位器候选"
        if not isinstance(payload, dict) or not payload:
            return "AI 返回内容未解析出有效 JSON 对象，无法读取定位器候选"
        candidate_fields = ("candidates", "locators", "recommendations", "results")
        containers = [payload]
        if isinstance(payload.get("data"), dict):
            containers.append(payload["data"])
        if any(
                isinstance(container.get(key), list) and not container.get(key)
                for container in containers
                for key in candidate_fields
        ):
            return "AI 明确返回了空候选列表，但未按约定说明无法生成的原因"
        return "AI 返回内容缺少 candidates 和 reason 字段，无法提取定位器候选"

    @staticmethod
    def _extract_ai_reason(payload) -> str:
        if not isinstance(payload, dict):
            return "AI 返回内容不是有效的 JSON 对象"
        containers = [payload]
        if isinstance(payload.get("data"), dict):
            containers.append(payload["data"])
        for container in containers:
            for key in ("reason", "message", "explanation"):
                value = ElementAiDataSanitizer.text(container.get(key), 500).strip()
                if value:
                    return value
        return ""

    @staticmethod
    def _extract_candidate_rows(payload) -> list[dict]:
        """Accept common model response wrappers without weakening locator validation."""
        if not isinstance(payload, dict):
            return []
        containers = [payload]
        if isinstance(payload.get("data"), dict):
            containers.append(payload["data"])
        for container in containers:
            for key in ("candidates", "locators", "recommendations", "results"):
                rows = container.get(key)
                if isinstance(rows, list):
                    return rows
        return []

    @classmethod
    def _normalize_candidate(cls, item) -> dict | None:
        if not isinstance(item, dict):
            return None
        strategy = str(
            item.get("strategy") or item.get("type") or item.get("method") or ""
        ).strip().lower()
        strategy = {
            "get_by_role": "role",
            "get_by_label": "label",
            "get_by_placeholder": "placeholder",
            "get_by_text": "text",
            "get_by_test_id": "testid",
            "test_id": "testid",
            "get_by_title": "title",
            "get_by_alt_text": "alt_text",
            "css_selector": "css",
            "selector": "css",
        }.get(strategy, strategy)

        direct_locator = ElementAiDataSanitizer.text(
            item.get("locator") or item.get("loc") or item.get("expression"), 1000
        ).strip()
        if direct_locator:
            direct = cls._normalize_direct_locator(item.get("exp"), direct_locator)
            if direct:
                return cls._build_candidate(
                    compiled=direct,
                    strategy=cls._strategy_from_exp(direct["exp"], direct["loc"]),
                    item=item,
                )

        if strategy not in cls.ALLOWED_STRATEGIES:
            return None
        value = ElementAiDataSanitizer.text(
            item.get("value")
            or item.get("name")
            or item.get("accessible_name")
            or item.get("selector")
            or (direct_locator if strategy in {"css", "xpath"} else ""),
            1000,
        ).strip()
        if not value:
            return None
        exact = bool(item.get("exact", True))
        compiled = cls._compile_locator(strategy, value, item.get("role"), exact)
        if not compiled:
            return None
        return cls._build_candidate(compiled=compiled, strategy=strategy, item=item)

    @classmethod
    def _build_candidate(cls, compiled: dict, strategy: str, item: dict) -> dict:
        try:
            confidence = max(0, min(100, int(item.get("confidence") or 0)))
        except (TypeError, ValueError):
            confidence = 0
        candidate = {
            **compiled,
            "strategy": strategy,
            "source": "ai_recommendation",
            "reason": ElementAiDataSanitizer.text(item.get("reason"), 300),
            "confidence": confidence,
            "verified": False,
            "count": 0,
        }
        candidate["candidate_id"] = hashlib.sha256(
            cls._candidate_identity(candidate).encode("utf-8")
        ).hexdigest()[:16]
        return candidate

    @classmethod
    def _normalize_direct_locator(cls, exp, locator: str) -> dict | None:
        locator = locator.strip()
        if locator.startswith("page."):
            locator = locator[5:]
        try:
            exp_value = int(exp) if exp is not None else None
        except (TypeError, ValueError):
            exp_value = None
        if exp_value == 0 or (exp_value is None and locator.startswith(("/", "("))):
            return {"exp": 0, "loc": locator} if locator.startswith(("/", "(")) else None
        if exp_value == 9:
            return {"exp": 9, "loc": locator}
        if exp_value not in (None, 2):
            return None

        role_match = re.fullmatch(
            r'get_by_role\(("(?:\\.|[^"\\])*")\s*,\s*name=("(?:\\.|[^"\\])*")'
            r'(?:\s*,\s*exact=(True|False))?\)',
            locator,
        )
        if role_match:
            try:
                role = json.loads(role_match.group(1))
                value = json.loads(role_match.group(2))
            except json.JSONDecodeError:
                return None
            return cls._compile_locator(
                "role", value, role, role_match.group(3) != "False"
            )

        semantic_match = re.fullmatch(
            r'get_by_(label|placeholder|text|test_id|title|alt_text)'
            r'\(("(?:\\.|[^"\\])*")(?:\s*,\s*exact=(True|False))?\)',
            locator,
        )
        if not semantic_match:
            return None
        try:
            value = json.loads(semantic_match.group(2))
        except json.JSONDecodeError:
            return None
        strategy = {
            "test_id": "testid",
        }.get(semantic_match.group(1), semantic_match.group(1))
        return cls._compile_locator(
            strategy, value, None, semantic_match.group(3) != "False"
        )

    @staticmethod
    def _strategy_from_exp(exp: int, locator: str) -> str:
        if exp == 0:
            return "xpath"
        if exp == 9:
            return "css"
        method = re.match(r"get_by_([a-z_]+)\(", locator)
        if not method:
            return "text"
        return {"test_id": "testid"}.get(method.group(1), method.group(1))

    @staticmethod
    def _build_diagnostics(
            generated_count: int,
            available_count: int,
            invalid_count: int,
            duplicate_count: int,
            ai_reason: str = "",
            model_attempts: int = 1,
    ) -> dict:
        if available_count:
            message = f"AI 返回 {generated_count} 个候选，本批可用 {available_count} 个"
        elif not generated_count:
            message = ai_reason or "AI 返回内容不符合定位器推荐协议，未提供候选及原因"
        elif invalid_count == generated_count:
            message = f"AI 返回了 {generated_count} 个候选，但格式均不受支持，请点击“换一批”"
        elif duplicate_count:
            message = f"AI 返回的 {generated_count} 个候选均与已有定位器重复，请点击“换一批”"
        else:
            message = "当前批次没有可用的定位器候选，请点击“换一批”"
        return {
            "generated_count": generated_count,
            "available_count": available_count,
            "invalid_count": invalid_count,
            "duplicate_count": duplicate_count,
            "ai_reason": ai_reason,
            "model_attempts": model_attempts,
            "message": message,
        }

    @staticmethod
    def _compile_locator(strategy: str, value: str, role, exact: bool) -> dict | None:
        quoted = json.dumps(value, ensure_ascii=False)
        exact_text = "True" if exact else "False"
        if strategy == "role":
            role_value = ElementAiDataSanitizer.text(role, 80).strip().lower()
            if not role_value.replace("_", "").replace("-", "").isalnum():
                return None
            return {
                "exp": 2,
                "loc": (
                    f"get_by_role({json.dumps(role_value)}, name={quoted}, exact={exact_text})"
                ),
            }
        method_map = {
            "label": "get_by_label",
            "placeholder": "get_by_placeholder",
            "text": "get_by_text",
            "testid": "get_by_test_id",
            "title": "get_by_title",
            "alt_text": "get_by_alt_text",
        }
        if strategy in method_map:
            exact_arg = "" if strategy == "testid" else f", exact={exact_text}"
            return {"exp": 2, "loc": f"{method_map[strategy]}({quoted}{exact_arg})"}
        if strategy == "css":
            return {"exp": 9, "loc": value}
        if strategy == "xpath" and value.startswith(("/", "(")):
            return {"exp": 0, "loc": value}
        return None

    @classmethod
    def _sanitize_context(cls, context: dict) -> dict:
        context = ElementAiDataSanitizer.json_value(context or {})
        baseline = ElementAiDataSanitizer.snapshot(context.get("baseline_snapshot") or {})
        return {
            "tag": ElementAiDataSanitizer.text(context.get("tag"), 80),
            "role": ElementAiDataSanitizer.text(context.get("role"), 80),
            "text": ElementAiDataSanitizer.text(context.get("text"), 500),
            "label": ElementAiDataSanitizer.text(context.get("label"), 500),
            "accessible_name": ElementAiDataSanitizer.text(
                context.get("accessible_name"), 500
            ),
            "placeholder": ElementAiDataSanitizer.text(context.get("placeholder"), 500),
            "attributes": ElementAiDataSanitizer.attributes(context.get("attributes") or {}),
            "frame_depth": context.get("frame_depth") or 0,
            "shadow_depth": context.get("shadow_depth") or 0,
            "baseline_snapshot": baseline,
        }

    @staticmethod
    def _sanitize_user_guidance(data: dict) -> dict:
        return {
            "location_description": ElementAiDataSanitizer.text(
                data.get("location_description"), 1000
            ).strip(),
            "surrounding_text": ElementAiDataSanitizer.text(
                data.get("surrounding_text"), 500
            ).strip(),
        }

    @staticmethod
    def _has_target_context(context: dict) -> bool:
        return any(
            context.get(key)
            for key in ("tag", "role", "text", "label", "accessible_name", "placeholder")
        ) or bool((context.get("baseline_snapshot") or {}).get("outer_html"))

    @staticmethod
    def _candidate_identity(candidate: dict) -> str:
        return f"{candidate.get('exp')}:{str(candidate.get('loc') or '').strip()}"

    @classmethod
    def _cache_key(cls, snapshot_id: str) -> str:
        return f"{cls.CACHE_PREFIX}{snapshot_id}"
