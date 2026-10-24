# -*- coding: utf-8 -*-
"""
功能测试用例 AI 生成耗时探测脚本。

示例：
    cd MangoServer
    .venv/bin/python scripts/benchmarks/functional_case_agent_benchmark.py --env=dev --suite-id=1 --mode=direct
    .venv/bin/python scripts/benchmarks/functional_case_agent_benchmark.py --env=dev --suite-id=1 --mode=full

默认只生成预览，不写入平台用例；需要真实落库时显式追加 --write。
"""
import argparse
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def find_server_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").exists():
            return parent
    raise RuntimeError("无法定位 MangoServer 目录")


BASE_DIR = find_server_dir()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def setup_django(env: str):
    os.environ["DJANGO_ENV"] = env
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")
    import django

    django.setup()


@contextmanager
def timer(label: str, timings: list[tuple[str, float]]):
    start = time.perf_counter()
    print(f"\n>>> {label} ...", flush=True)
    try:
        yield
    finally:
        cost = time.perf_counter() - start
        timings.append((label, cost))
        print(f"<<< {label}: {cost:.2f}s", flush=True)


def parse_context_keys(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or None


def preview_result(suite, payload: dict, write: bool, user_id: int | None):
    from src.apps.ai.agent.functional_case.generator import FunctionalCaseGenerator
    from src.apps.functional_test.services.case_sync import FunctionalTestCaseSyncService
    from src.apps.functional_test.services.suite import ManualTestSuiteService

    normalized = FunctionalCaseGenerator.normalize(payload)
    preview = ManualTestSuiteService.sync_preview(suite, normalized)
    if write:
        FunctionalTestCaseSyncService.sync_confirm(suite, preview, user_id)
    return preview


def print_preview(preview: dict):
    cases = preview.get("cases") or []
    validation = preview.get("validation") or {}
    changes = preview.get("changes") or []
    print("\n=== Result ===")
    print(f"case_count: {len(cases)}")
    print(f"validation: {validation}")
    if changes:
        change_counter: dict[Any, int] = {}
        for item in changes:
            key = item.get("change_status")
            change_counter[key] = change_counter.get(key, 0) + 1
        print(f"changes: {change_counter}")
    for index, item in enumerate(cases[:5], start=1):
        print(f"sample_{index}: {item.get('case_no') or '-'} / {item.get('title') or '-'}")


def run_direct(args, suite, context_payload, skill, ai_role: str | None):
    from src.apps.ai.services.agent.document import AgentDocumentService
    from src.apps.ai.agent.functional_case.batch_generator import FunctionalCaseBatchGenerator
    from src.apps.ai.agent.functional_case.generator import FunctionalCaseGenerator

    timings: list[tuple[str, float]] = []
    with timer("读取资料", timings):
        doc = AgentDocumentService.read_document("", context_payload["ai_source_content"])

    with timer("AI直接生成平台用例JSON", timings):
        payload = FunctionalCaseBatchGenerator.generate_direct_cases(
            source_content=doc["content"],
            requirement_context=context_payload["selected_context"],
            user_instruction=args.instruction or "",
            skill=skill,
            ai_role=ai_role,
            task=None,
            max_tokens=args.max_tokens,
        )
    if args.deep_check:
        with timer("深度补漏", timings):
            payload = FunctionalCaseGenerator.deep_patch_cases(
                generated_payload=payload,
                source_content=doc["content"],
                requirement_context=context_payload["selected_context"],
                user_instruction=args.instruction or "",
                skill=skill,
                ai_role=ai_role,
                task=None,
            )

    with timer("规范化与预览", timings):
        preview = preview_result(suite, payload, args.write, args.user_id)

    return timings, preview


def run_full(args, suite, context_payload, skill, ai_role: str | None):
    from src.apps.ai.services.agent.document import AgentDocumentService
    from src.apps.ai.agent.functional_case.generator import FunctionalCaseGenerator

    timings: list[tuple[str, float]] = []
    with timer("读取资料", timings):
        doc = AgentDocumentService.read_document("", context_payload["ai_source_content"])

    with timer("需求理解", timings):
        requirement_analysis = FunctionalCaseGenerator.analyze_requirement(
            requirement_context=context_payload["selected_context"],
            source_content=doc["content"],
            user_instruction=args.instruction or "",
            skill=skill,
            ai_role=ai_role,
            task=None,
        )

    with timer("已有覆盖识别", timings):
        existing_coverage = FunctionalCaseGenerator.analyze_existing_coverage(
            requirement_analysis=requirement_analysis,
            source_content=doc["content"],
            user_instruction=args.instruction or "",
            skill=skill,
            ai_role=ai_role,
            task=None,
        )

    with timer("覆盖差异分析", timings):
        gap_analysis = FunctionalCaseGenerator.analyze_gap(
            requirement_analysis=requirement_analysis,
            existing_coverage=existing_coverage,
            user_instruction=args.instruction or "",
            skill=skill,
            ai_role=ai_role,
            task=None,
        )

    outline = {
        "suite": {},
        "outline": gap_analysis.get("generation_outline") or [],
        "requirement_analysis": requirement_analysis,
        "existing_coverage": existing_coverage,
        "gap_analysis": gap_analysis,
        "warnings": [
            *(requirement_analysis.get("warnings") or []),
            *(existing_coverage.get("warnings") or []),
            *(gap_analysis.get("warnings") or []),
        ],
    }

    with timer("分片生成用例", timings):
        payload = FunctionalCaseGenerator.generate_cases(
            source_content=doc["content"],
            requirement_context=context_payload["selected_context"],
            outline=outline,
            user_instruction=args.instruction or "",
            skill=skill,
            ai_role=ai_role,
            task=None,
        )

    with timer("覆盖校验补漏", timings):
        payload = FunctionalCaseGenerator.coverage_check_and_patch(
            generated_payload=payload,
            source_content=doc["content"],
            requirement_context=context_payload["selected_context"],
            outline=outline,
            user_instruction=args.instruction or "",
            skill=skill,
            ai_role=ai_role,
            task=None,
        )

    with timer("规范化与预览", timings):
        preview = preview_result(suite, payload, args.write, args.user_id)

    return timings, preview


def main():
    parser = argparse.ArgumentParser(description="功能测试用例 AI 生成耗时探测")
    parser.add_argument("--env", default="dev", help="Django 环境，默认 dev")
    parser.add_argument("--suite-id", type=int, required=True, help="功能测试需求 ID")
    parser.add_argument("--mode", choices=["direct", "full"], default="direct", help="direct=快速直出，full=测试设计全链路")
    parser.add_argument("--context-keys", default="", help="逗号分隔的上下文 key；不传则使用默认选择")
    parser.add_argument("--skill-id", type=int, default=None, help="功能测试技能 ID；不传使用默认功能测试技能")
    parser.add_argument("--ai-role", default=None, help="AI 角色；不传使用业务测试专家")
    parser.add_argument("--instruction", default="", help="补充要求")
    parser.add_argument("--max-tokens", type=int, default=16000, help="direct 模式单次最大输出 token")
    parser.add_argument("--deep-check", action="store_true", help="direct 模式生成后追加一次深度补漏")
    parser.add_argument("--write", action="store_true", help="生成后真实写入平台用例")
    parser.add_argument("--user-id", type=int, default=None, help="写入时使用的用户 ID")
    args = parser.parse_args()

    setup_django(args.env)

    from src.apps.ai.services.agent.context import AgentContextService
    from src.apps.ai.agent.roles import AgentRole
    from src.apps.ai.services.skill.service import AgentSkillService
    from src.apps.functional_test.models import ManualTestSuite
    from src.apps.ai.enums import AiSkillTypeEnum

    suite = ManualTestSuite.objects.get(id=args.suite_id)
    skill = AgentSkillService.get_skill(skill_id=args.skill_id) if args.skill_id else AgentSkillService.get_default_functional_case_skill()
    if getattr(skill, "id", None) and getattr(skill, "skill_type", None) != AiSkillTypeEnum.FUNCTIONAL_TEST.value:
        raise ValueError("功能用例生成只能使用功能测试类型的技能")
    ai_role = AgentRole.normalize(args.ai_role, AgentRole.BUSINESS_TEST_EXPERT)

    timings: list[tuple[str, float]] = []
    with timer("构建上下文", timings):
        context_payload = AgentContextService.build_functional_suite_context(
            suite,
            parse_context_keys(args.context_keys),
        )

    print("\n=== Input ===")
    print(f"suite_id: {suite.id}")
    print(f"requirement_name: {suite.requirement_name}")
    print(f"mode: {args.mode}")
    print(f"write: {args.write}")
    print(f"context_keys: {context_payload.get('context_keys')}")
    print(f"context_hash: {context_payload.get('context_hash')}")
    print(f"source_size: {len(context_payload.get('ai_source_content') or '')}")
    print(f"selected_context_size: {len(context_payload.get('selected_context') or '')}")
    print(f"skill: {getattr(skill, 'id', None)} / {getattr(skill, 'name', '')}")
    print(f"ai_role: {ai_role}")

    total_start = time.perf_counter()
    if args.mode == "direct":
        run_timings, preview = run_direct(args, suite, context_payload, skill, ai_role)
    else:
        run_timings, preview = run_full(args, suite, context_payload, skill, ai_role)
    total_cost = time.perf_counter() - total_start
    timings.extend(run_timings)

    print_preview(preview)
    print("\n=== Timings ===")
    for label, cost in timings:
        print(f"{label}: {cost:.2f}s")
    print(f"total_without_context: {total_cost:.2f}s")
    print(f"total: {sum(cost for _, cost in timings):.2f}s")


if __name__ == "__main__":
    main()
