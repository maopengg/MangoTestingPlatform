# -*- coding: utf-8 -*-
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from django.db import close_old_connections

from src.apps.ai.agent.functional_case.prompt import CASE_SCHEMA_PROMPT, build_system_prompt
from src.apps.ai.context import StructuredContextCompiler
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.services.core import AiTaskService, extract_ai_json
from src.common.prompts.functional_test import render_functional_case_prompt


class FunctionalCaseBatchGenerator:
    MAX_PARALLEL_CHUNKS = 3

    @classmethod
    def generate_cases(
            cls,
            *,
            source_content: str,
            requirement_context: str,
            outline: dict,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
            max_tokens: int,
    ) -> dict:
        plan_batches = cls.build_plan_batches(outline.get("outline") or [])
        if not plan_batches:
            plan_batches = [
                {
                    "group_name": "完整测试设计",
                    "expected_case_count": 0,
                    "case_titles": [],
                    "purpose": "full_design",
                }
            ]
        cases: list[dict] = []
        warnings: list[Any] = list(outline.get("warnings") or [])
        seen = set()
        if task:
            AiTaskService.update_progress(
                task,
                32,
                "请求已经发给 AI",
                f"正在按测试计划分批生成，共 {len(plan_batches)} 批",
                {"batch_total": len(plan_batches), "batch_done": 0,
                 "parallel_batches": min(cls.MAX_PARALLEL_CHUNKS, len(plan_batches))},
            )
        results = cls.generate_plan_batches_parallel(
            plan_batches=plan_batches,
            source_content=source_content,
            requirement_context=requirement_context,
            outline=outline,
            user_instruction=user_instruction,
            skill=skill,
            ai_role=ai_role,
            task=task,
            max_tokens=max_tokens,
        )
        for index in sorted(results):
            payload = results[index]
            warnings.extend(payload.get("warnings") or [])
            for item in payload.get("cases") or []:
                key = item.get("source_hash") or item.get("source_text") or item.get("title") or json.dumps(item,
                                                                                                            ensure_ascii=False,
                                                                                                            sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                cases.append(item)
        return {"suite": outline.get("suite") or {}, "cases": cases, "warnings": warnings}

    @classmethod
    def generate_plan_batches_parallel(
            cls,
            *,
            plan_batches: list[dict],
            source_content: str,
            requirement_context: str,
            outline: dict,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None,
            max_tokens: int,
    ) -> dict[int, dict]:
        batch_total = len(plan_batches)
        if not batch_total:
            return {}
        worker_count = min(cls.MAX_PARALLEL_CHUNKS, batch_total)
        results: dict[int, dict] = {}
        done_count = 0

        def run_batch(index: int, plan_batch: dict) -> tuple[int, dict]:
            close_old_connections()
            try:
                thread_task = AiAgentTask.objects.get(id=task.id) if task else None
                payload = cls.generate_plan_batch(
                    plan_batch=plan_batch,
                    batch_index=index,
                    batch_total=batch_total,
                    source_context=cls.select_source_context(source_content, plan_batch),
                    requirement_context=requirement_context,
                    outline=outline,
                    user_instruction=user_instruction,
                    skill=skill,
                    ai_role=ai_role,
                    task=thread_task,
                    max_tokens=max_tokens,
                )
                return index, payload
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(run_batch, index, plan_batch): index
                for index, plan_batch in enumerate(plan_batches, start=1)
            }
            for future in as_completed(future_map):
                index, payload = future.result()
                results[index] = payload
                done_count += 1
                if task:
                    AiTaskService.update_progress(
                        task,
                        min(40 + int(done_count / max(batch_total, 1) * 30), 70),
                        "JSON 解析完成",
                        f"测试计划批次已完成 {done_count}/{batch_total}",
                        {"batch_index": index, "batch_total": batch_total, "batch_done": done_count},
                    )
        return results

    @classmethod
    def generate_plan_batch(
            cls,
            *,
            plan_batch: dict,
            batch_index: int,
            batch_total: int,
            source_context: str,
            requirement_context: str,
            outline: dict,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
            max_tokens: int,
    ) -> dict:
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "batch_generation",
                    batch_index=batch_index,
                    batch_total=batch_total,
                    user_instruction=user_instruction,
                    plan_batch=json.dumps(plan_batch, ensure_ascii=False),
                    outline=json.dumps(outline, ensure_ascii=False)[:24000],
                    requirement_context=StructuredContextCompiler.select(
                        requirement_context, json.dumps(plan_batch, ensure_ascii=False), 12000
                    ),
                    source_context=source_context,
                    case_schema=CASE_SCHEMA_PROMPT,
                ),
            },
        ]
        if task:
            AiTaskService.update_progress(
                task,
                min(40 + int(batch_index / max(batch_total, 1) * 25), 66),
                "请求已经发给 AI",
                f"正在等待测试计划批次 {batch_index}/{batch_total} 返回",
                {"batch_index": batch_index, "batch_total": batch_total},
            )
        response = AgentModelGateway.json_chat(task=task, messages=messages, max_tokens=max_tokens)
        if task:
            AiTaskService.update_progress(
                task,
                min(45 + int(batch_index / max(batch_total, 1) * 30), 70),
                "JSON 解析完成",
                f"测试计划批次 {batch_index}/{batch_total} 已解析",
                {"batch_index": batch_index, "batch_total": batch_total},
            )
        return extract_ai_json(response, task=task)

    @staticmethod
    def build_plan_batches(outline: list[dict], max_titles: int = 15) -> list[dict]:
        batches = []
        for item in outline:
            if not isinstance(item, dict):
                continue
            titles = [str(title).strip() for title in item.get("case_titles") or [] if str(title).strip()]
            if not titles:
                batches.append(dict(item))
                continue
            for start in range(0, len(titles), max_titles):
                batch = dict(item)
                batch["case_titles"] = titles[start:start + max_titles]
                batch["expected_case_count"] = len(batch["case_titles"])
                batches.append(batch)
        return batches

    @classmethod
    def select_source_context(cls, source_content: str, plan_batch: dict, limit: int = 18000) -> str:
        text = source_content or ""
        if len(text) <= limit:
            return text
        terms = cls.plan_terms(plan_batch)
        sections = cls.source_sections(text)
        scored = []
        for index, section in enumerate(sections):
            normalized = section.lower()
            score = sum(3 for term in terms if term and term in normalized)
            if section.lstrip().startswith("|"):
                score += 1
            scored.append((score, index, section))
        selected = []
        total = 0
        for score, _, section in sorted(scored, key=lambda item: (-item[0], item[1])):
            if score <= 0 and selected:
                continue
            if total + len(section) > limit and selected:
                continue
            selected.append(section)
            total += len(section)
            if total >= limit:
                break
        if not selected:
            return StructuredContextCompiler.select(
                text,
                json.dumps(plan_batch, ensure_ascii=False),
                limit,
            )
        return StructuredContextCompiler.select(
            "\n\n".join(selected),
            json.dumps(plan_batch, ensure_ascii=False),
            limit,
        )

    @staticmethod
    def plan_terms(plan_batch: dict) -> set[str]:
        values = [plan_batch.get("group_name") or "", *(plan_batch.get("case_titles") or [])]
        terms = set()
        for value in values:
            text = str(value).lower()
            terms.update(token for token in re.split(r"[^\w\u4e00-\u9fff]+", text) if len(token) >= 2)
            terms.update(text[index:index + 4] for index in range(0, max(len(text) - 3, 0), 4))
        return terms

    @staticmethod
    def source_sections(text: str) -> list[str]:
        sections = []
        current = []
        for line in text.splitlines():
            starts_section = bool(re.match(r"^#{1,6}\s+", line)) or (
                    line.strip().startswith("|") and current and not current[-1].strip().startswith("|")
            )
            if starts_section and current:
                sections.append("\n".join(current))
                current = []
            current.append(line)
            if line.strip().startswith("|") and len("\n".join(current)) >= 3000:
                sections.append("\n".join(current))
                current = []
        if current:
            sections.append("\n".join(current))
        return [section for section in sections if section.strip()]
