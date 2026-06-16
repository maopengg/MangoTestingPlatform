# -*- coding: utf-8 -*-
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from django.db import close_old_connections

from src.apps.ai.agent.functional_case.content_splitter import FunctionalCaseContentSplitter
from src.apps.ai.agent.functional_case.schema import CASE_SCHEMA_PROMPT, build_system_prompt
from src.apps.ai.models import AiAgentTask, AiSkill
from src.apps.ai.service.core import AiTaskService, extract_ai_json
from src.apps.system.service.ai.client import AiService


class FunctionalCaseBatchGenerator:
    MAX_PARALLEL_CHUNKS = 3

    @classmethod
    def generate_direct_cases(
        cls,
        *,
        source_content: str,
        requirement_context: str,
        user_instruction: str,
        skill: AiSkill | None,
        ai_role: str | None,
        task: AiAgentTask | None = None,
        max_tokens: int,
    ) -> dict:
        chunks = FunctionalCaseContentSplitter.split_content(source_content, 5000)
        if len(chunks) > 1:
            if task:
                AiTaskService.update_progress(
                    task,
                    25,
                    "请求已经发给 AI",
                    f"正在快速分片生成平台用例，共 {len(chunks)} 片",
                    {"chunk_total": len(chunks), "chunk_done": 0, "generate_mode": "direct_chunked"},
                )
            results = cls.generate_direct_chunks_parallel(
                chunks=chunks,
                requirement_context=requirement_context,
                user_instruction=user_instruction,
                skill=skill,
                ai_role=ai_role,
                task=task,
                max_tokens=max_tokens,
            )
            return cls.merge_payloads([results[index] for index in sorted(results)])

        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": (
                    "请根据下面的需求资料、测试描述和已选择上下文，直接生成测试平台功能用例 JSON。"
                    "如果上下文中包含原始用例文档，优先保留其中每一条用例；也可以只根据需求文档、页面数据或测试理解直接设计用例。"
                    "用例编号统一按 FT-{四位序号} 生成，不要沿用原始编号，不要使用模块缩写。"
                    "如果需求文档中包含“测试平台用例”上下文，表示用户要在已有平台用例基础上重新编辑：匹配到已有用例时必须保持已有 case_no 不变，只修改其他字段；只有新增场景才分配新的 FT 编号。"
                    "不要先输出分析过程，不要输出 Markdown，不要只返回示例，不要限制为 10 条。"
                    f"\n补充要求：{user_instruction}"
                    f"\n需求相关上下文：\n{requirement_context[:30000]}"
                    f"\n测试设计上下文：\n{source_content[:100000]}"
                    f"\n\n{CASE_SCHEMA_PROMPT}"
                ),
            },
        ]
        if task:
            AiTaskService.update_progress(
                task,
                35,
                "请求已经发给 AI",
                "正在生成测试平台用例 JSON",
                {"generate_mode": "direct"},
            )
        response = AiService.json_chat(messages, max_tokens=max(max_tokens, 16000))
        if task:
            AiTaskService.update_progress(
                task,
                70,
                "JSON 解析完成",
                "测试平台用例 JSON 已返回",
                {"generate_mode": "direct"},
            )
        return extract_ai_json(response)

    @classmethod
    def generate_direct_chunks_parallel(
        cls,
        *,
        chunks: list[str],
        requirement_context: str,
        user_instruction: str,
        skill: AiSkill | None,
        ai_role: str | None,
        task: AiAgentTask | None,
        max_tokens: int,
    ) -> dict[int, dict]:
        chunk_total = len(chunks)
        worker_count = min(cls.MAX_PARALLEL_CHUNKS, chunk_total)
        results: dict[int, dict] = {}
        done_count = 0

        def run_chunk(index: int, chunk: str) -> tuple[int, dict]:
            close_old_connections()
            try:
                return index, cls.generate_direct_chunk(
                    chunk=chunk,
                    chunk_index=index,
                    chunk_total=chunk_total,
                    requirement_context=requirement_context,
                    user_instruction=user_instruction,
                    skill=skill,
                    ai_role=ai_role,
                    max_tokens=max_tokens,
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(run_chunk, index, chunk): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in as_completed(future_map):
                index, payload = future.result()
                results[index] = payload
                done_count += 1
                if task:
                    AiTaskService.update_progress(
                        task,
                        min(35 + int(done_count / max(chunk_total, 1) * 35), 70),
                        "JSON 解析完成",
                        f"快速分片已完成 {done_count}/{chunk_total}",
                        {"chunk_index": index, "chunk_total": chunk_total, "chunk_done": done_count, "generate_mode": "direct_chunked"},
                    )
        return results

    @classmethod
    def generate_direct_chunk(
        cls,
        *,
        chunk: str,
        chunk_index: int,
        chunk_total: int,
        requirement_context: str,
        user_instruction: str,
        skill: AiSkill | None,
        ai_role: str | None,
        max_tokens: int,
    ) -> dict:
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": (
                    f"当前是第 {chunk_index}/{chunk_total} 个上下文资料分片。"
                    "请只根据当前分片转换或设计测试平台功能用例 JSON，不要生成其他分片内容。"
                    "如果当前分片包含明确用例，优先保留每一条；也可以根据需求描述、页面数据或测试理解补充应有用例。"
                    "用例编号统一按 FT-{四位序号} 生成，不要沿用原始编号，不要使用模块缩写。"
                    "如果需求文档摘要中包含“测试平台用例”上下文，表示用户要在已有平台用例基础上重新编辑：匹配到已有用例时必须保持已有 case_no 不变，只修改其他字段；只有新增场景才分配新的 FT 编号。"
                    "不要输出分析过程，不要输出 Markdown，不要只返回示例。"
                    f"\n补充要求：{user_instruction}"
                    f"\n需求相关上下文摘要：\n{requirement_context[:8000]}"
                    f"\n当前上下文资料分片：\n{chunk}"
                    f"\n\n{CASE_SCHEMA_PROMPT}"
                ),
            },
        ]
        response = AiService.json_chat(messages, max_tokens=max_tokens)
        return extract_ai_json(response)

    @staticmethod
    def merge_payloads(payloads: list[dict]) -> dict:
        cases: list[dict] = []
        warnings: list[Any] = []
        seen = set()
        suite = {}
        for payload in payloads:
            if not suite and isinstance(payload.get("suite"), dict):
                suite = payload.get("suite") or {}
            warnings.extend(payload.get("warnings") or [])
            for item in payload.get("cases") or []:
                key = item.get("source_hash") or item.get("source_text") or item.get("title") or json.dumps(item, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                cases.append(item)
        return {"suite": suite, "cases": cases, "warnings": warnings}

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
        chunk_size: int,
        max_tokens: int,
    ) -> dict:
        chunks = FunctionalCaseContentSplitter.split_content(source_content, chunk_size)
        cases: list[dict] = []
        warnings: list[Any] = list(outline.get("warnings") or [])
        seen = set()
        if task:
            AiTaskService.update_progress(
                task,
                32,
                "请求已经发给 AI",
                f"正在并发提交功能用例分片，共 {len(chunks)} 片",
                {"chunk_total": len(chunks), "chunk_done": 0, "parallel_chunks": min(cls.MAX_PARALLEL_CHUNKS, len(chunks))},
            )
        results = cls.generate_chunks_parallel(
            chunks=chunks,
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
                key = item.get("source_hash") or item.get("source_text") or item.get("title") or json.dumps(item, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                cases.append(item)
        return {"suite": outline.get("suite") or {}, "cases": cases, "warnings": warnings}

    @classmethod
    def generate_chunks_parallel(
        cls,
        *,
        chunks: list[str],
        requirement_context: str,
        outline: dict,
        user_instruction: str,
        skill: AiSkill | None,
        ai_role: str | None,
        task: AiAgentTask | None,
        max_tokens: int,
    ) -> dict[int, dict]:
        chunk_total = len(chunks)
        if not chunk_total:
            return {}
        worker_count = min(cls.MAX_PARALLEL_CHUNKS, chunk_total)
        results: dict[int, dict] = {}
        done_count = 0

        def run_chunk(index: int, chunk: str) -> tuple[int, dict]:
            close_old_connections()
            try:
                payload = cls.generate_chunk(
                    chunk=chunk,
                    chunk_index=index,
                    chunk_total=chunk_total,
                    requirement_context=requirement_context if index == 1 else "",
                    outline=outline,
                    user_instruction=user_instruction,
                    skill=skill,
                    ai_role=ai_role,
                    task=None,
                    max_tokens=max_tokens,
                )
                return index, payload
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(run_chunk, index, chunk): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in as_completed(future_map):
                index, payload = future.result()
                results[index] = payload
                done_count += 1
                if task:
                    AiTaskService.update_progress(
                        task,
                        min(40 + int(done_count / max(chunk_total, 1) * 30), 70),
                        "JSON 解析完成",
                        f"功能用例分片已完成 {done_count}/{chunk_total}",
                        {"chunk_index": index, "chunk_total": chunk_total, "chunk_done": done_count},
                    )
        return results

    @classmethod
    def generate_chunk(
        cls,
        *,
        chunk: str,
        chunk_index: int,
        chunk_total: int,
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
                "content": (
                    f"当前是第 {chunk_index}/{chunk_total} 个资料分片。请完整生成本分片中所有明确出现或能直接推导的用例。"
                    "同时必须参考差异分析，补齐缺失的验收点、异常、边界、权限、数据和流程场景。"
                    "不要生成其他分片内容，不要只返回示例，不要限制为 10 条。"
                    f"\n补充要求：{user_instruction}"
                    f"\n测试设计分析：{json.dumps(outline, ensure_ascii=False)[:24000]}"
                    f"\n需求相关上下文：\n{requirement_context[:8000]}"
                    f"\n当前分片资料：\n{chunk}"
                    f"\n\n{CASE_SCHEMA_PROMPT}"
                ),
            },
        ]
        if task:
            AiTaskService.update_progress(
                task,
                min(40 + int(chunk_index / max(chunk_total, 1) * 25), 66),
                "请求已经发给 AI",
                f"正在等待用例分片 {chunk_index}/{chunk_total} 返回",
                {"chunk_index": chunk_index, "chunk_total": chunk_total},
            )
        response = AiService.json_chat(messages, max_tokens=max_tokens)
        if task:
            AiTaskService.update_progress(
                task,
                min(45 + int(chunk_index / max(chunk_total, 1) * 30), 70),
                "JSON 解析完成",
                f"用例分片 {chunk_index}/{chunk_total} 已解析",
                {"chunk_index": chunk_index, "chunk_total": chunk_total},
            )
        return extract_ai_json(response)
