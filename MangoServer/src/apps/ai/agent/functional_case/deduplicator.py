# -*- coding: utf-8 -*-
import json
import re
from difflib import SequenceMatcher

from src.apps.ai.agent.functional_case.prompt import build_system_prompt
from src.apps.ai.model_gateway.client import AgentModelGateway
from src.apps.ai.services.core import extract_ai_json
from src.common.prompts.functional_test import render_functional_case_prompt


class FunctionalCaseDeduplicator:
    @classmethod
    def deduplicate(cls, payload: dict, *, skill=None, ai_role=None, task=None) -> tuple[dict, dict]:
        cases = list(payload.get("cases") or [])
        kept = []
        exact_index = {}
        merged = []
        for item in cases:
            fingerprint = cls.fingerprint(item)
            if fingerprint in exact_index:
                merged.append(
                    {
                        "kept_title": exact_index[fingerprint].get("title"),
                        "merged_title": item.get("title"),
                        "merge_reason": "规范化字段完全一致",
                        "source_refs": [exact_index[fingerprint].get("source_text"), item.get("source_text")],
                    }
                )
                continue
            exact_index[fingerprint] = item
            kept.append(item)

        candidate_pairs = cls.near_duplicate_pairs(kept)
        if candidate_pairs:
            decisions = cls.semantic_decisions(kept, candidate_pairs, skill, ai_role, task)
            remove_indexes = set()
            for decision in decisions:
                kept_index = decision.get("kept_index")
                duplicate_index = decision.get("duplicate_index")
                if not isinstance(kept_index, int) or not isinstance(duplicate_index, int):
                    continue
                if kept_index == duplicate_index or not (0 <= kept_index < len(kept)) or not (
                        0 <= duplicate_index < len(kept)):
                    continue
                remove_indexes.add(duplicate_index)
                merged.append(
                    {
                        "kept_title": kept[kept_index].get("title"),
                        "merged_title": kept[duplicate_index].get("title"),
                        "merge_reason": decision.get("reason") or "语义重复",
                        "source_refs": [kept[kept_index].get("source_text"), kept[duplicate_index].get("source_text")],
                    }
                )
            kept = [item for index, item in enumerate(kept) if index not in remove_indexes]

        result = dict(payload)
        result["cases"] = kept
        report = {
            "before_count": len(cases),
            "after_count": len(kept),
            "candidate_pair_count": len(candidate_pairs),
            "merged": merged,
        }
        return result, report

    @staticmethod
    def fingerprint(item: dict) -> str:
        values = [
            item.get("title"),
            item.get("precondition"),
            item.get("test_point"),
            item.get("test_data"),
            item.get("scenario_type"),
        ]
        return "|".join(re.sub(r"\s+", "", str(value or "")).lower() for value in values)

    @classmethod
    def near_duplicate_pairs(cls, cases: list[dict], limit: int = 50) -> list[dict]:
        pairs = []
        for left in range(len(cases)):
            left_text = cls.fingerprint(cases[left])
            for right in range(left + 1, len(cases)):
                similarity = SequenceMatcher(None, left_text, cls.fingerprint(cases[right])).ratio()
                if similarity >= 0.82:
                    pairs.append({"left": left, "right": right, "similarity": round(similarity, 3)})
                    if len(pairs) >= limit:
                        return pairs
        return pairs

    @staticmethod
    def semantic_decisions(cases: list[dict], pairs: list[dict], skill, ai_role, task=None) -> list[dict]:
        candidates = [
            {
                **pair,
                "left_case": cases[pair["left"]],
                "right_case": cases[pair["right"]],
            }
            for pair in pairs
        ]
        messages = [
            {"role": "system", "content": build_system_prompt(skill, ai_role)},
            {
                "role": "user",
                "content": render_functional_case_prompt(
                    "semantic_deduplication",
                    candidates=json.dumps(candidates, ensure_ascii=False)[:50000],
                ),
            },
        ]
        payload = extract_ai_json(
            AgentModelGateway.json_chat(
                task=task,
                messages=messages,
                temperature=0,
                max_tokens=4000,
            ),
            task=task,
        )
        return payload.get("duplicates") or []
