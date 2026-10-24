# -*- coding: utf-8 -*-
from src.apps.ai.agent.functional_case.batch_generator import FunctionalCaseBatchGenerator
from src.apps.ai.agent.functional_case.coverage_checker import FunctionalCaseCoverageChecker
from src.apps.ai.agent.functional_case.deduplicator import FunctionalCaseDeduplicator
from src.apps.ai.agent.functional_case.design_analyzer import FunctionalCaseDesignAnalyzer
from src.apps.ai.agent.functional_case.normalizer import FunctionalCaseNormalizer
from src.apps.ai.agent.functional_case.planner import FunctionalCaseOutlinePlanner
from src.apps.ai.agent.functional_case.prompt import CASE_SCHEMA_PROMPT, build_system_prompt
from src.apps.ai.models import AiAgentTask, AiSkill


class FunctionalCaseGenerator:
    MAX_TOKENS = 8000
    CASE_SCHEMA_PROMPT = CASE_SCHEMA_PROMPT

    analyze_requirement = FunctionalCaseDesignAnalyzer.analyze_requirement
    analyze_existing_coverage = FunctionalCaseDesignAnalyzer.analyze_existing_coverage
    analyze_gap = FunctionalCaseDesignAnalyzer.analyze_gap
    finalize_coverage_matrix = FunctionalCaseDesignAnalyzer.finalize_coverage_matrix
    compose_case_plan = FunctionalCaseOutlinePlanner.compose_case_plan
    deduplicate = FunctionalCaseDeduplicator.deduplicate

    @classmethod
    def build_outline(
            cls,
            *,
            source_content: str,
            requirement_context: str,
            user_instruction: str,
            skill: AiSkill | None,
            ai_role: str | None,
            task: AiAgentTask | None = None,
    ) -> dict:
        return FunctionalCaseOutlinePlanner.build_outline(
            source_content=source_content,
            requirement_context=requirement_context,
            user_instruction=user_instruction,
            skill=skill,
            ai_role=ai_role,
            task=task,
        )

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
    ) -> dict:
        return FunctionalCaseBatchGenerator.generate_cases(
            source_content=source_content,
            requirement_context=requirement_context,
            outline=outline,
            user_instruction=user_instruction,
            skill=skill,
            ai_role=ai_role,
            task=task,
            max_tokens=cls.MAX_TOKENS,
        )

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
        return FunctionalCaseCoverageChecker.coverage_check_and_patch(
            generated_payload=generated_payload,
            source_content=source_content,
            requirement_context=requirement_context,
            outline=outline,
            user_instruction=user_instruction,
            skill=skill,
            ai_role=ai_role,
            task=task,
        )

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
        return FunctionalCaseCoverageChecker.deep_patch_cases(
            generated_payload=generated_payload,
            source_content=source_content,
            requirement_context=requirement_context,
            user_instruction=user_instruction,
            skill=skill,
            ai_role=ai_role,
            task=task,
        )

    evaluate_final_coverage = FunctionalCaseCoverageChecker.evaluate_final_coverage
    repair_findings = FunctionalCaseCoverageChecker.repair_findings

    @classmethod
    def normalize(cls, payload: dict) -> dict:
        return FunctionalCaseNormalizer.normalize(payload)

    @classmethod
    def _system_prompt(cls, skill: AiSkill | None, ai_role: str | None) -> str:
        return build_system_prompt(skill, ai_role)
