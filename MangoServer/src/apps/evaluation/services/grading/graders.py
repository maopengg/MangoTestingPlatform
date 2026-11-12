import jsonschema
import json
import math
import inspect
from functools import lru_cache
import re
from collections import Counter
from src.apps.system.services.ai.json_output import extract_ai_json
from src.apps.evaluation.exceptions import EvaluationError
from src.apps.evaluation.formatters.payload import canonical_json, content_hash, select_value
from src.apps.evaluation.schemas import GraderMetric, GraderResult
from src.apps.evaluation.schemas.grader import ModelJudgeOutput
from src.apps.evaluation.services.assets.validation import invalid_config
from src.apps.evaluation.services.model.ai import json_chat
from src.common.prompts.evaluation_judge import (
    EVALUATION_JUDGE_PROMPT_VERSION,
    build_evaluation_judge_messages,
)
from src.apps.evaluation.services.grading.memory_grading import MemoryScoringService


_MISSING_VALUE = object()


def _values(dataset_item, actual, config):
    expected = select_value(dataset_item.get("expected_output") or {}, config.get("expected_path"), _MISSING_VALUE)
    if expected is _MISSING_VALUE:
        raise invalid_config("评分器配置的期望字段路径不存在")
    actual_value = select_value(actual, config.get("actual_path"))
    return expected, actual_value


class BaseGrader:
    key = "base"
    version = 1

    @classmethod
    def evaluate(cls, *, dataset_item: dict, actual: dict, config: dict, metric_key: str, threshold: float):
        raise NotImplementedError

    @staticmethod
    def result(metric_key, *, raw_value, score, passed, evidence=None, reason="", confidence=1.0, requires_review=False):
        return GraderResult(metrics=[GraderMetric(
            key=metric_key, raw_value=raw_value, score=score, passed=passed,
            evidence=evidence or {}, reason=reason, confidence=confidence,
        )], requires_review=requires_review)


class ExactMatchGrader(BaseGrader):
    key = "exact_match"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        normalize = config.get("normalize") or {}
        if normalize.get("trim") and isinstance(expected, str) and isinstance(actual_value, str):
            expected, actual_value = expected.strip(), actual_value.strip()
        if normalize.get("casefold") and isinstance(expected, str) and isinstance(actual_value, str):
            expected, actual_value = expected.casefold(), actual_value.casefold()
        actual_exists = select_value(actual, config.get("actual_path"), _MISSING_VALUE) is not _MISSING_VALUE
        passed = actual_exists and actual_value == expected
        return cls.result(metric_key, raw_value=passed, score=100 if passed else 0, passed=passed,
                          evidence={"expected": expected, "actual": actual_value},
                          reason="实际值与期望值一致" if passed else "实际值与期望值不一致")


class ContainsGrader(BaseGrader):
    key = "contains"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        values = expected if isinstance(expected, list) else [expected]
        text = str(actual_value or "")
        matched = [value for value in values if value is not None and str(value) in text]
        ratio = len(matched) / len(values) if values else 1
        score = ratio * 100
        passed = score >= threshold
        return cls.result(metric_key, raw_value=ratio, score=score, passed=passed,
                          evidence={"expected": values, "matched": matched},
                          reason=f"命中 {len(matched)}/{len(values)} 项")


class SetMatchGrader(BaseGrader):
    key = "set_match"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        if not isinstance(expected, list):
            raise invalid_config("集合评分的期望字段必须是数组")
        if not isinstance(actual_value, list):
            return cls.result(metric_key, raw_value=None, score=0, passed=False,
                              evidence={"actual_type": type(actual_value).__name__}, reason="实际输出不是数组，不能视为空集合")
        expected_set = {canonical_json(item) for item in (expected or [])}
        actual_set = {canonical_json(item) for item in (actual_value or [])}
        true_positive = len(expected_set & actual_set)
        precision = true_positive / len(actual_set) if actual_set else (1 if not expected_set else 0)
        recall = true_positive / len(expected_set) if expected_set else (1 if not actual_set else 0)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        score = f1 * 100
        passed = score >= threshold
        metrics = [
            GraderMetric(key=metric_key, raw_value=f1, score=score, passed=passed,
                            evidence={"missing": sorted(expected_set-actual_set), "unexpected": sorted(actual_set-expected_set)},
                            reason=f"集合F1={score:.2f}", confidence=1),
            GraderMetric(key=f"{metric_key}_precision", raw_value=precision, score=precision*100,
                            passed=precision*100 >= threshold, reason=f"Precision={precision*100:.2f}", confidence=1),
            GraderMetric(key=f"{metric_key}_recall", raw_value=recall, score=recall*100,
                            passed=recall*100 >= threshold, reason=f"Recall={recall*100:.2f}", confidence=1),
        ]
        return GraderResult(metrics=metrics)


class NumericToleranceGrader(BaseGrader):
    key = "numeric_tolerance"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        try:
            expected_number, actual_number = float(expected), float(actual_value)
            absolute_error = abs(actual_number - expected_number)
            tolerance = float(config.get("absolute_tolerance", 0))
            relative_tolerance = float(config.get("relative_tolerance", 0))
            allowed = max(tolerance, abs(expected_number) * relative_tolerance)
            passed = absolute_error <= allowed
            score = 100 if passed else max(0, 100 * (1 - absolute_error / max(abs(expected_number), 1)))
        except (TypeError, ValueError):
            absolute_error, allowed, passed, score = None, None, False, 0
        return cls.result(metric_key, raw_value=absolute_error, score=score, passed=passed,
                          evidence={"expected": expected, "actual": actual_value, "allowed_error": allowed},
                          reason="数值在容差内" if passed else "数值超出容差")


class JsonSchemaGrader(BaseGrader):
    key = "json_schema"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        if "schema" not in config and not config.get("expected_path") and not dataset_item.get("expected_output"):
            raise invalid_config("请为 JSON Schema 评分配置明确的标准")
        schema = config["schema"] if "schema" in config else select_value(
            dataset_item.get("expected_output") or {}, config.get("expected_path"),
        )
        if not isinstance(schema, (dict, bool)):
            raise invalid_config("JSON Schema 评分标准不存在或不是合法 Schema")
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.SchemaError as error:
            raise invalid_config("JSON Schema 评分标准不合法") from error
        actual_value = select_value(actual, config.get("actual_path"))
        try:
            jsonschema.validate(actual_value, schema)
            return cls.result(metric_key, raw_value=True, score=100, passed=True, reason="输出符合Schema")
        except jsonschema.ValidationError as error:
            return cls.result(metric_key, raw_value=False, score=0, passed=False,
                              evidence={"path": list(getattr(error, "path", []))}, reason=str(error.message)[:500])


class BehaviorGrader(ExactMatchGrader):
    key = "behavior"


class ClassificationGrader(BaseGrader):
    key = "classification"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        passed = expected == actual_value
        return cls.result(
            metric_key,
            raw_value={"expected": expected, "actual": actual_value},
            score=100 if passed else 0,
            passed=passed,
            evidence={"expected_label": expected, "actual_label": actual_value},
            reason="分类正确" if passed else "分类错误",
        )


class FieldExtractionGrader(BaseGrader):
    key = "field_extraction"

    @staticmethod
    def _flatten(value, prefix=""):
        if not isinstance(value, dict):
            return {prefix or "$": canonical_json(value)}
        result = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, dict):
                result.update(FieldExtractionGrader._flatten(item, path))
            else:
                result[path] = canonical_json(item)
        return result

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        expected_fields = cls._flatten(expected or {})
        actual_fields = cls._flatten(actual_value or {})
        matched = {key for key, value in expected_fields.items() if actual_fields.get(key) == value}
        precision = len(matched) / len(actual_fields) if actual_fields else (1 if not expected_fields else 0)
        recall = len(matched) / len(expected_fields) if expected_fields else (1 if not actual_fields else 0)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        score = f1 * 100
        return GraderResult(metrics=[
            GraderMetric(
                key=metric_key, raw_value=f1, score=score, passed=score >= threshold,
                evidence={
                    "missing_fields": sorted(expected_fields.keys() - actual_fields.keys()),
                    "unexpected_fields": sorted(actual_fields.keys() - expected_fields.keys()),
                    "incorrect_fields": sorted(
                        key for key in expected_fields.keys() & actual_fields.keys()
                        if expected_fields[key] != actual_fields[key]
                    ),
                },
                reason=f"字段F1={score:.2f}", confidence=1,
            ),
            GraderMetric(key=f"{metric_key}_precision", raw_value=precision, score=precision*100, passed=precision*100 >= threshold),
            GraderMetric(key=f"{metric_key}_recall", raw_value=recall, score=recall*100, passed=recall*100 >= threshold),
        ])


class RankingGrader(BaseGrader):
    key = "ranking"
    version = 2

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        if not isinstance(expected, list):
            raise invalid_config("排序评分的预期相关项必须是数组")
        if not isinstance(actual_value, list):
            raise invalid_config("排序评分的实际结果必须是数组")
        relevant = list({canonical_json(item): item for item in expected}.values())
        ranked = actual_value
        k = max(1, int(config.get("k") or len(ranked) or len(relevant) or 1))
        top = ranked[:k]
        relevant_set = {canonical_json(item) for item in relevant}
        top_keys = [canonical_json(item) for item in top]
        seen = set()
        hits = []
        for index, item in enumerate(top_keys, start=1):
            if item in relevant_set and item not in seen:
                hits.append(index)
            seen.add(item)
        reciprocal_rank = 1 / hits[0] if hits else 0
        empty_correct = not ranked
        recall = len(set(top_keys) & relevant_set) / len(relevant_set) if relevant_set else float(empty_correct)
        dcg = sum(1 / math.log2(index + 1) for index in hits)
        ideal_count = min(len(relevant_set), k)
        idcg = sum(1 / math.log2(index + 1) for index in range(1, ideal_count + 1))
        ndcg = dcg / idcg if idcg else float(empty_correct)
        if not relevant_set:
            reciprocal_rank = float(empty_correct)
        score = ndcg * 100
        return GraderResult(metrics=[
            GraderMetric(key=metric_key, raw_value=ndcg, score=score, passed=score >= threshold, reason=f"NDCG@{k}={score:.2f}"),
            GraderMetric(key=f"{metric_key}_mrr", raw_value=reciprocal_rank, score=reciprocal_rank*100, passed=reciprocal_rank*100 >= threshold),
            GraderMetric(key=f"{metric_key}_recall_at_k", raw_value=recall, score=recall*100, passed=recall*100 >= threshold),
        ])


class TextTokenF1Grader(BaseGrader):
    key = "text_token_f1"

    @staticmethod
    def _tokens(value):
        return re.findall(r"[\w\u4e00-\u9fff]+", str(value or "").casefold())

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        expected, actual_value = _values(dataset_item, actual, config)
        expected_counter = Counter(cls._tokens(expected))
        actual_counter = Counter(cls._tokens(actual_value))
        common = sum((expected_counter & actual_counter).values())
        precision = common / sum(actual_counter.values()) if actual_counter else (1 if not expected_counter else 0)
        recall = common / sum(expected_counter.values()) if expected_counter else (1 if not actual_counter else 0)
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        return cls.result(metric_key, raw_value=f1, score=f1*100, passed=f1*100 >= threshold, reason=f"Token F1={f1*100:.2f}")


class ModelJudgeGrader(BaseGrader):
    key = "model_judge"

    @classmethod
    def evaluate(cls, *, dataset_item, actual, config, metric_key, threshold):
        judge_snapshot = config.get("_judge_snapshot") or {}
        response = json_chat(frozen=judge_snapshot, prompt_id="evaluation.judge",
            messages=build_evaluation_judge_messages(
                dataset_item=dataset_item, actual=actual, rubric=config.get("rubric") or {}, metric_key=metric_key,
            ),
            temperature=0,
            max_tokens=int(config.get("max_tokens") or 1500),
        )
        parsed = ModelJudgeOutput.model_validate(extract_ai_json(response))
        data = parsed.model_dump(mode="json")
        data.update(judge_prompt_version=EVALUATION_JUDGE_PROMPT_VERSION, judge_provider=judge_snapshot["provider"], judge_model=judge_snapshot["model"])
        uncertain = not bool(parsed.evidence) or parsed.requires_review or parsed.confidence < float(config.get("confidence_threshold", 0.7))
        return cls.result(metric_key, raw_value=data, score=parsed.score,
                          passed=parsed.passed and parsed.score >= threshold and not uncertain,
                          evidence=parsed.evidence, reason=parsed.reason,
                          confidence=parsed.confidence, requires_review=uncertain)



class MemoryGrader(BaseGrader):
    @classmethod
    def evaluate(cls, **kwargs):
        return MemoryScoringService.evaluate(task=cls.key, **kwargs)


class MemoryQAGrader(MemoryGrader):
    key = "memory_qa"
    version = 2


class MemoryExtractionGrader(MemoryGrader):
    key = "memory_extraction"


class MemoryUpdateGrader(MemoryGrader):
    key = "memory_update"


class EvaluationGraderRegistry:
    graders = {
        grader.key: grader for grader in (
            ExactMatchGrader, ContainsGrader, SetMatchGrader,
            NumericToleranceGrader, JsonSchemaGrader, BehaviorGrader,
            ClassificationGrader, FieldExtractionGrader, RankingGrader,
            TextTokenF1Grader, ModelJudgeGrader, MemoryQAGrader, MemoryExtractionGrader, MemoryUpdateGrader,
        )
    }
    names = {
        "exact_match": "精确匹配", "contains": "内容包含", "set_match": "集合匹配",
        "numeric_tolerance": "数值容差", "json_schema": "JSON Schema", "behavior": "行为匹配",
        "model_judge": "LLM 裁判", "classification": "分类准确性", "field_extraction": "字段抽取 F1",
        "ranking": "检索排序", "text_token_f1": "文本 Token F1",
        "memory_qa": "记忆问答正确性",
        "memory_extraction": "记忆提取", "memory_update": "记忆更新",
    }
    parameter_extensions = {
        "exact_match": {"normalize": {"type": "object", "additionalProperties": False, "properties": {"trim": {"type": "boolean"}, "casefold": {"type": "boolean"}}}},
        "behavior": {"normalize": {"type": "object", "additionalProperties": False, "properties": {"trim": {"type": "boolean"}, "casefold": {"type": "boolean"}}}},
        "numeric_tolerance": {"absolute_tolerance": {"type": "number", "minimum": 0}, "relative_tolerance": {"type": "number", "minimum": 0}},
        "json_schema": {"schema": {"type": "object"}},
        "model_judge": {"rubric": {"type": "object"}, "max_tokens": {"type": "integer", "minimum": 100, "maximum": 8000}, "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 1}},
        "memory_qa": {"max_tokens": {"type": "integer", "minimum": 100, "maximum": 16000}},
        "memory_extraction": {"max_tokens": {"type": "integer", "minimum": 100, "maximum": 16000}},
        "memory_update": {"max_tokens": {"type": "integer", "minimum": 100, "maximum": 16000}},
        "ranking": {"k": {"type": "integer", "minimum": 1}},
    }

    @classmethod
    def parameter_schema(cls, key):
        properties = {"expected_path": {"type": "string", "description": "预期对象中的字段路径，空值为整个对象"},
                      "actual_path": {"type": "string", "description": "实际输出中的字段路径，空值为整个对象"},
                      **cls.parameter_extensions.get(key, {})}
        if cls.get(key) and cls.is_model(key):
            properties.pop("expected_path")
            properties.pop("actual_path")
        return {"type": "object", "properties": properties, "additionalProperties": False}

    @classmethod
    @lru_cache(maxsize=128)
    def implementation_hash(cls, key, version=1):
        grader, _ = cls.resolve(key, version)
        if grader is None:
            return None
        lineage = [inspect.getsource(base) for base in grader.__mro__ if base not in (object,)]
        if issubclass(grader, MemoryGrader):
            lineage.append(inspect.getsource(MemoryScoringService))
        return content_hash({"source": lineage, "values": inspect.getsource(_values), "schema": cls.parameter_schema(key), "version": version})

    @classmethod
    def get(cls, key):
        return cls.graders.get(key)

    @classmethod
    def is_model(cls, key):
        grader = cls.get(key)
        return grader is ModelJudgeGrader or bool(grader and issubclass(grader, MemoryGrader))

    @classmethod
    def prompt_id(cls, key):
        return "evaluation.memory_scoring" if issubclass(cls.get(key), MemoryGrader) else "evaluation.judge"

    @classmethod
    def resolve(cls, key, version=1):
        grader = cls.get(key)
        if grader:
            return (grader, {}) if grader.version == version else (None, {})
        return None, {}

    @classmethod
    def validate_config(cls, key, version, config):
        grader, defaults = cls.resolve(key, version)
        if not grader:
            return None
        merged = {**defaults, **(config or {})}
        try:
            json.dumps(merged, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise jsonschema.ValidationError("参数必须是有限数值组成的 JSON") from error
        jsonschema.validate(merged, cls.parameter_schema(grader.key))
        if key == "json_schema" and "schema" in merged:
            jsonschema.Draft202012Validator.check_schema(merged["schema"])
        return merged

    @classmethod
    def validate_result(cls, key, version, result):
        GraderResult.model_validate(result.model_dump(mode="json"))

    @classmethod
    def catalog(cls):
        descriptions = {
            "exact_match": "规范化后精确比较；适合明确答案和结构化值。",
            "contains": "按预期关键词命中比例评分；不能代替事实完整性核对。",
            "set_match": "集合 Precision/Recall/F1；输出附带缺失与多余项。",
            "numeric_tolerance": "检查绝对或相对误差，保留原始数值误差。",
            "json_schema": "检查实际对象是否满足已固定的 JSON Schema。",
            "behavior": "对拒答、澄清、回答等业务行为进行精确比较。",
            "classification": "计算单条分类正确性，执行内提供混淆矩阵。",
            "field_extraction": "按字段路径和值比较，计算抽取 Precision/Recall/F1。",
            "ranking": "固定 K 值与相关项，计算 NDCG/MRR/Recall@K。",
            "text_token_f1": "按分词计数计算文本重合 F1；不等同于语义正确性。",
            "model_judge": "按固定 Rubric 与模型/提示词评分；证据不足或低置信度为无效。",
            "memory_qa": "逐项核对标准答案必要事实与原文证据；区分正确、幻觉、遗漏，正确100其余0；证据不可核对时无效，置信度仅供诊断。",
            "memory_extraction": "逐项核对标准记忆覆盖与实际记忆事实支持；完整记1、部分记0.5、错误或遗漏记0，计算语义 Precision/Recall/F1。",
            "memory_update": "核对新事实完整生效、旧事实被替换或标为历史；正确100，幻觉或遗漏0，无法核对时无效。",
        }
        values = {
            "contains": (["每周", "周二"], "每周周二开会"),
            "set_match": (["A", "B"], ["A", "B"]),
            "numeric_tolerance": (10, 10), "classification": ("positive", "positive"),
            "behavior": ("refuse", "refuse"), "ranking": (["A", "B"], ["A", "B"]),
            "text_token_f1": ("项目负责人 张三", "项目负责人 张三"),
        }
        records = []
        for key, grader in cls.graders.items():
            expected, actual = values.get(key, ({"answer": "张三"}, {"answer": "张三"}))
            if key == "json_schema":
                expected = {"type": "object", "required": ["answer"]}
            if key == "memory_extraction":
                expected, actual = {"memories": ["张三住在北京"]}, ["张三住在北京"]
            if key == "memory_update":
                expected, actual = {"updates": [{"before": "张三住在上海", "after": "张三现住北京"}]}, ["张三现住北京"]
            sample = {"expected_output": expected, "actual_output": actual, "parameters": {}}
            if issubclass(grader, MemoryGrader):
                sample["input_data"] = "张三现在住哪里？" if key == "memory_qa" else "张三从上海搬到了北京。"
                sample["context"] = {"source_evidence": [{"excerpt": "张三从上海搬到了北京。"}]}
                if key == "memory_qa":
                    sample.update(expected_output={"answer": "北京", "facts": ["张三现住北京"]}, actual_output="张三现住北京")
            sample["expected_result"] = {"note": "需有金标准和原文证据；示例不发起模型调用"} if cls.is_model(key) else {"score": 100, "passed": True}
            records.append({
                "grader_key": key, "grader_version": grader.version, "name": cls.names[key],
                "category": "model" if cls.is_model(key) else "algorithm" if key in {"classification", "field_extraction", "ranking", "text_token_f1", "set_match"} else "deterministic",
                "description": descriptions[key], "supported_tasks": ["semantic"] if cls.is_model(key) else ["structured", "text"],
                "parameters_schema": cls.parameter_schema(key), "implementation_hash": cls.implementation_hash(key, grader.version),
                "score_scale": {"minimum": 0, "maximum": 100},
                "output": {"score": "0~100", "passed": "boolean", "reason": "评分理由", "evidence": "可核对证据", "confidence": "0~1 或 null"},
                "examples": [sample],
                "uncertainty_rule": "核对项不完整、引用不匹配或无法判定时标记无效；模型置信度仅供诊断" if issubclass(grader, MemoryGrader) else "格式错误、置信度不足或无法判定时标记无效" if cls.is_model(key) else "按固定字段与指标定义判断，执行错误不算能力零分",
            })
        return records
