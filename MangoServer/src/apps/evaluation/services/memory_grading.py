"""Evidence-checked memory judgments; numeric scores are computed outside the model."""
import json
from src.apps.evaluation.enums.answer import EvaluationAnswerVerdictEnum as Verdict
from src.apps.evaluation.enums.memory import MemoryFactStatusEnum as Status
from src.apps.evaluation.schemas.grader import GraderMetric, GraderResult
from src.apps.evaluation.schemas.memory import MemoryJudgment
from src.apps.evaluation.services.ai import json_chat
from src.apps.evaluation.services.answer import strict_model_output
from src.apps.evaluation.services.validation import invalid_config
from src.common.prompts import get_prompt


class MemoryScoringService:
    @staticmethod
    def text_leaves(value):
        if isinstance(value, dict):
            return [text for child in value.values() for text in MemoryScoringService.text_leaves(child)]
        if isinstance(value, list):
            return [text for child in value for text in MemoryScoringService.text_leaves(child)]
        return [value] if isinstance(value, str) and value.strip() else []

    @staticmethod
    def memories(value, label):
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise invalid_config(f"{label}必须是非空文本组成的数组；没有记忆时使用空数组")
        return value

    @classmethod
    def evaluate(cls, *, task, dataset_item, actual, config, metric_key, threshold):
        gold = dataset_item.get("expected_output")
        sources = (dataset_item.get("context") or {}).get("source_evidence")
        source_texts = cls.text_leaves(sources)
        if not isinstance(gold, dict) or not source_texts:
            raise invalid_config("记忆评分需要结构化标准和 context.source_evidence 原文证据")
        original = []
        if task == "memory_qa":
            answer = actual if isinstance(actual, str) else actual.get("answer") if isinstance(actual, dict) else None
            if not isinstance(answer, str) or not isinstance(gold.get("answer"), str) or not gold["answer"].strip():
                raise invalid_config("记忆问答需要实际回答文本和 expected_output.answer 标准答案")
            expected = cls.memories(gold.get("facts", [gold["answer"]]), "标准答案事实")
            if not expected:
                raise invalid_config("标准答案事实不能为空")
            observed = [answer] if answer.strip() else []
        elif task == "memory_extraction":
            expected = cls.memories(gold.get("memories"), "标准记忆")
            observed = cls.memories(actual, "实际记忆")
        elif task == "memory_update":
            updates = gold.get("updates")
            if not isinstance(updates, list) or not updates or any(
                not isinstance(item, dict) or set(item) != {"before", "after"} or
                any(not isinstance(item[key], str) or not item[key].strip() for key in ("before", "after"))
                for item in updates
            ):
                raise invalid_config("记忆更新需要 expected_output.updates 数组，每项为 before、after 非空文本")
            original = [item["before"] for item in updates]
            expected = [item["after"] for item in updates]
            observed = cls.memories(actual, "更新后记忆")
        else:
            raise invalid_config("未注册的记忆评分任务")
        question = dataset_item.get("input_data")
        if isinstance(question, dict):
            question = question.get("query", question)
        prompt = get_prompt("evaluation.memory_scoring")
        response = json_chat(frozen=config.get("_judge_snapshot") or {}, prompt_id=prompt.id,
            messages=[{"role": "system", "content": prompt.system + "\n" + prompt.values[task]},
                      {"role": "user", "content": json.dumps({"question": question, "expected": expected,
                       "original_memories": original, "source_evidence": sources, "actual": observed}, ensure_ascii=False)}],
            temperature=0, max_tokens=int(config.get("max_tokens") or 4000))
        judgment = MemoryJudgment.model_validate(strict_model_output(response))
        grounded = cls.check_evidence(judgment, expected, observed, source_texts, task)
        review = judgment.requires_review or not grounded
        raw = judgment.model_dump(mode="json")
        # Model confidence is diagnostic; it is not a calibrated probability of correctness.
        raw["judge_model"] = config.get("_judge_snapshot")
        raw["evidence_verified"] = grounded
        score, extras = cls.scores(task, judgment, expected, observed)
        statuses = [check.status for check in judgment.expected_checks + judgment.actual_checks]
        hallucination = any(check.status in {Status.PARTIAL, Status.UNSUPPORTED, Status.CONTRADICTED}
                            for check in judgment.actual_checks) or Status.CONTRADICTED in statuses
        omitted = any(check.status in {Status.OMITTED, Status.PARTIAL} for check in judgment.expected_checks)
        verdict = Verdict.HALLUCINATION if hallucination else Verdict.OMISSION if omitted else Verdict.CORRECT
        if task != "memory_extraction":
            raw["classification"] = verdict.value
            score = 100 if verdict == Verdict.CORRECT else 0
        metrics = [GraderMetric(key=metric_key, raw_value=raw, score=None if review else score,
            passed=not review and score >= threshold and (task == "memory_extraction" or verdict == Verdict.CORRECT),
            reason=judgment.reason, evidence={"expected_checks": raw["expected_checks"], "actual_checks": raw["actual_checks"]},
            confidence=judgment.confidence)]
        for suffix, value in extras.items():
            metrics.append(GraderMetric(key=metric_key + suffix, raw_value=value,
                score=None if review else value * 100, passed=not review and value * 100 >= threshold,
                reason=judgment.reason, confidence=judgment.confidence))
        return GraderResult(metrics=metrics, requires_review=review)

    @staticmethod
    def check_evidence(judgment, expected, observed, sources, task):
        for checks, entries, actual_side in ((judgment.expected_checks, expected, False), (judgment.actual_checks, observed, True)):
            if sorted(check.index for check in checks) != list(range(len(entries))):
                return False
            for check in checks:
                allowed = {Status.SUPPORTED, Status.PARTIAL, Status.UNSUPPORTED, Status.CONTRADICTED} if actual_side else {
                    Status.SUPPORTED, Status.PARTIAL, Status.OMITTED, Status.CONTRADICTED}
                if actual_side and task == "memory_qa":
                    allowed.add(Status.ABSTAINED)
                if actual_side and task == "memory_update":
                    allowed.add(Status.UNCHANGED)
                if check.status not in allowed:
                    return False
                absence = actual_side and check.status in {Status.UNSUPPORTED, Status.ABSTAINED}
                if not absence and not check.source_quote.strip():
                    return False
                if check.source_quote and not any(check.source_quote in source for source in sources):
                    return False
                candidates = [entries[check.index]] if actual_side else observed
                if check.status == Status.OMITTED and not actual_side:
                    if check.actual_quote and not any(check.actual_quote in item for item in candidates):
                        return False
                elif not check.actual_quote.strip() or not any(check.actual_quote in item for item in candidates):
                    return False
        return True

    @staticmethod
    def scores(task, judgment, expected, observed):
        if task != "memory_extraction":
            return 0, {}
        def credit(check):
            return 1 if check.status == Status.SUPPORTED else 0.5 if check.status == Status.PARTIAL else 0
        recall = sum(credit(check) for check in judgment.expected_checks) / len(expected) if expected else 1.0
        precision = sum(credit(check) for check in judgment.actual_checks) / len(observed) if observed else (1.0 if not expected else 0.0)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return f1 * 100, {"_precision": precision, "_recall": recall}
