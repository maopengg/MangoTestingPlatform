# -*- coding: utf-8 -*-
import json

from src.apps.ai.agent.functional_case.prompt import CASE_SCHEMA_PROMPT, build_system_prompt
from src.apps.ai.context import StructuredContextCompiler
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.services.core import AiTaskService, extract_ai_json
from src.common.prompts.functional_test import render_functional_case_prompt


class FunctionalCaseCoverageChecker:
    @classmethod
    def coverage_check_and_patch(
            cls,
            *,
            generated_payload: dict,
            source_content: str,
            requirement_context: str,
            outline: dict,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 68, "请求已经发给 AI", "正在核对遗漏场景并补漏")
        case_digest = [
            {
                "case_no": item.get("case_no"),
                "title": item.get("title"),
                "test_point": item.get("test_point"),
                "scenario_type": item.get("scenario_type"),
            }
            for item in (generated_payload.get("cases") or [])
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "coverage_patch",
                    user_instruction=user_instruction,
                    outline=json.dumps(outline, ensure_ascii=False)[:16000],
                    case_digest=json.dumps(case_digest, ensure_ascii=False)[:24000],
                    requirement_context=StructuredContextCompiler.select(
                        requirement_context, "验收点 风险 权限 边界 异常 流程", 8000
                    ),
                    source_content=StructuredContextCompiler.select(
                        source_content, json.dumps(outline, ensure_ascii=False)[:4000], 16000
                    ),
                    case_schema=CASE_SCHEMA_PROMPT,
                ),
            },
        ]
        response = AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=8000)
        patch_payload = extract_ai_json(response, task=task)
        existing = generated_payload.get("cases") or []
        seen = {item.get("source_hash") or item.get("source_text") or item.get("title") for item in existing}
        for item in patch_payload.get("cases") or []:
            key = item.get("source_hash") or item.get("source_text") or item.get("title")
            if key and key not in seen:
                existing.append(item)
                seen.add(key)
        generated_payload["cases"] = existing
        generated_payload.setdefault("warnings", []).extend(patch_payload.get("warnings") or [])
        return generated_payload

    @classmethod
    def deep_patch_cases(
            cls,
            *,
            generated_payload: dict,
            source_content: str,
            requirement_context: str,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 72, "深度补漏", "正在核对遗漏用例")
        case_digest = [
            {
                "case_no": item.get("case_no"),
                "title": item.get("title"),
                "test_point": item.get("test_point"),
                "scenario_type": item.get("scenario_type"),
                "source_text": item.get("source_text"),
            }
            for item in (generated_payload.get("cases") or [])
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "deep_patch",
                    user_instruction=user_instruction,
                    case_digest=json.dumps(case_digest, ensure_ascii=False)[:50000],
                    requirement_context=StructuredContextCompiler.select(
                        requirement_context, "验收点 异常 边界 权限 数据 流程", 12000
                    ),
                    source_content=StructuredContextCompiler.select(
                        source_content, json.dumps(case_digest, ensure_ascii=False)[:4000], 30000
                    ),
                    case_schema=CASE_SCHEMA_PROMPT,
                ),
            },
        ]
        response = AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=8000)
        patch_payload = extract_ai_json(response, task=task)
        existing = generated_payload.get("cases") or []
        seen = {item.get("source_hash") or item.get("source_text") or item.get("title") for item in existing}
        added_count = 0
        for item in patch_payload.get("cases") or []:
            key = item.get("source_hash") or item.get("source_text") or item.get("title")
            if key and key not in seen:
                existing.append(item)
                seen.add(key)
                added_count += 1
        generated_payload["cases"] = existing
        generated_payload.setdefault("warnings", []).extend(patch_payload.get("warnings") or [])
        generated_payload["deep_patch"] = {"added_count": added_count}
        if task:
            AiTaskService.update_progress(task, 80, "深度补漏", f"补漏完成，新增 {added_count} 条用例")
        return generated_payload

    @classmethod
    def evaluate_final_coverage(
            cls,
            *,
            generated_payload: dict,
            requirement_model: dict,
            coverage_matrix: dict,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 76, "覆盖质量门禁", "正在核对验收点、场景维度、重复和矛盾")
        case_digest = [
            {
                "case_no": item.get("case_no"),
                "title": item.get("title"),
                "test_point": item.get("test_point"),
                "precondition": item.get("precondition"),
                "scenario_type": item.get("scenario_type"),
                "scenario_layer": item.get("scenario_layer"),
                "story_refs": item.get("story_refs") or [],
                "acceptance_source": item.get("acceptance_source"),
                "source_text": item.get("source_text"),
            }
            for item in (generated_payload.get("cases") or [])
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "quality_gate",
                    user_instruction=user_instruction,
                    requirement_model=json.dumps(requirement_model, ensure_ascii=False)[:24000],
                    coverage_matrix=json.dumps(coverage_matrix, ensure_ascii=False)[:24000],
                    case_digest=json.dumps(case_digest, ensure_ascii=False)[:50000],
                ),
            },
        ]
        report = extract_ai_json(
            AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=6000),
            task=task,
        )
        findings = [item for item in report.get("findings") or [] if isinstance(item, dict)]
        criterion_ids = {
            str(item.get("criterion_id"))
            for item in requirement_model.get("acceptance_criteria") or []
            if isinstance(item, dict) and item.get("criterion_id")
        }
        referenced_ids = set()
        for index, case in enumerate(generated_payload.get("cases") or [], start=1):
            case_ref = case.get("case_no") or case.get("title") or f"第 {index} 条用例"
            refs = {
                str(item).strip()
                for item in case.get("story_refs") or []
                if str(item).strip()
            }
            referenced_ids.update(refs & criterion_ids)
            traceability_errors = []
            if criterion_ids and not refs:
                traceability_errors.append("未关联验收点 ID")
            invalid_refs = sorted(refs - criterion_ids)
            if invalid_refs:
                traceability_errors.append(f"引用了不存在的验收点：{'、'.join(invalid_refs)}")
            if not str(case.get("acceptance_source") or "").strip():
                traceability_errors.append("缺少验收规则来源")
            if not str(case.get("source_text") or "").strip():
                traceability_errors.append("缺少原始资料片段")
            if traceability_errors:
                findings.append(
                    {
                        "severity": "high",
                        "type": "traceability",
                        "message": f"{case_ref}：{'；'.join(traceability_errors)}",
                        "criterion_ids": sorted(refs),
                        "related_case_nos": [case.get("case_no")] if case.get("case_no") else [],
                    }
                )
        deterministic_missing = sorted(criterion_ids - referenced_ids)
        missing = sorted(
            {
                str(item)
                for item in report.get("missing_criterion_ids") or []
                if item
            }
            | set(deterministic_missing)
        )
        high_findings = [item for item in findings if str(item.get("severity") or "").lower() == "high"]
        report["findings"] = findings
        report["missing_criterion_ids"] = missing
        report["passed"] = not missing and not high_findings and bool(generated_payload.get("cases"))
        try:
            report["score"] = max(0, min(100, float(report.get("score", 100 if report["passed"] else 0))))
        except (TypeError, ValueError):
            report["score"] = 100 if report["passed"] else 0
        return report

    @classmethod
    def repair_findings(
            cls,
            *,
            generated_payload: dict,
            findings: list[dict],
            requirement_model: dict,
            source_content: str,
            requirement_context: str,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        if task:
            AiTaskService.update_progress(task, 80, "定向修复", "正在仅修复质量门禁发现的缺口")
        case_digest = [
            {
                "case_no": item.get("case_no"),
                "title": item.get("title"),
                "test_point": item.get("test_point"),
                "scenario_type": item.get("scenario_type"),
                "story_refs": item.get("story_refs") or [],
                "acceptance_source": item.get("acceptance_source"),
                "source_text": item.get("source_text"),
            }
            for item in (generated_payload.get("cases") or [])
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "repair_findings",
                    findings=json.dumps(findings, ensure_ascii=False)[:16000],
                    requirement_model=json.dumps(requirement_model, ensure_ascii=False)[:20000],
                    case_digest=json.dumps(case_digest, ensure_ascii=False)[:30000],
                    user_instruction=user_instruction,
                    requirement_context=StructuredContextCompiler.select(
                        requirement_context, json.dumps(findings, ensure_ascii=False), 10000
                    ),
                    source_content=StructuredContextCompiler.select(
                        source_content, json.dumps(findings, ensure_ascii=False), 18000
                    ),
                    case_schema=CASE_SCHEMA_PROMPT,
                ),
            },
        ]
        patch_payload = extract_ai_json(
            AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=8000),
            task=task,
        )
        existing = generated_payload.get("cases") or []
        by_case_no = {item.get("case_no"): index for index, item in enumerate(existing) if item.get("case_no")}
        by_title = {item.get("title"): index for index, item in enumerate(existing) if item.get("title")}
        seen = {item.get("source_hash") or item.get("source_text") or item.get("title") for item in existing}
        for item in patch_payload.get("cases") or []:
            existing_index = by_case_no.get(item.get("case_no")) if item.get("case_no") else None
            if existing_index is None:
                existing_index = by_title.get(item.get("title")) if item.get("title") else None
            if existing_index is not None:
                existing[existing_index] = {**existing[existing_index], **item}
                continue
            key = item.get("source_hash") or item.get("source_text") or item.get("title")
            if key and key not in seen:
                existing.append(item)
                seen.add(key)
        generated_payload["cases"] = existing
        generated_payload.setdefault("warnings", []).extend(patch_payload.get("warnings") or [])
        return generated_payload
