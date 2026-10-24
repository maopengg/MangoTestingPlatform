"""Synthetic human-labeled smoke samples, independent of any production dataset.

These are calibration seeds, not evidence of benchmark-level judge accuracy.
Expected classes/scores are fixed before model calls; never regenerate them from a judge.
"""

SOURCE = "Alice在1月住上海，2月1日搬到北京，此后未再次搬家。她的职业没有被提及。"
QA_GOLD = {"answer": "Alice现在住北京", "facts": ["Alice现在住北京"]}
UPDATE_GOLD = {"updates": [{"before": "Alice现在住上海", "after": "Alice现在住北京"}]}

SAMPLES = [
    {"name": "qa_paraphrase", "grader": "memory_qa", "question": "Alice现在住哪里？", "gold": QA_GOLD,
     "actual": "她目前居住在北京。", "classification": "correct", "score": 100},
    {"name": "qa_stale_fact", "grader": "memory_qa", "question": "Alice现在住哪里？", "gold": QA_GOLD,
     "actual": "Alice现在住上海。", "classification": "hallucination", "score": 0},
    {"name": "qa_missing_fact", "grader": "memory_qa", "question": "Alice现在住哪里？", "gold": QA_GOLD,
     "actual": "不知道。", "classification": "omission", "score": 0},
    {"name": "qa_correct_abstention", "grader": "memory_qa", "question": "Alice做什么工作？",
     "gold": {"answer": "无法确定Alice的职业"}, "actual": "现有信息无法确定她的职业。", "classification": "correct", "score": 100},
    {"name": "qa_fabricated_job", "grader": "memory_qa", "question": "Alice做什么工作？",
     "gold": {"answer": "无法确定Alice的职业"}, "actual": "她是一名医生。", "classification": "hallucination", "score": 0},
    {"name": "qa_missing_one_element", "grader": "memory_qa", "question": "Alice现在住哪里，何时搬去的？",
     "gold": {"answer": "Alice现在住北京，2月1日搬去", "facts": ["现在住北京", "2月1日搬去"]},
     "actual": "现在住北京。", "classification": "omission", "score": 0},
    {"name": "extraction_complete", "grader": "memory_extraction", "gold": {"memories": ["Alice现在住北京"]},
     "actual": ["Alice目前在北京居住"], "score": 100},
    {"name": "extraction_fabrication", "grader": "memory_extraction", "gold": {"memories": ["Alice现在住北京"]},
     "actual": ["Alice是医生"], "score": 0},
    {"name": "extraction_empty", "grader": "memory_extraction", "gold": {"memories": ["Alice现在住北京"]},
     "actual": [], "score": 0},
    {"name": "update_correct", "grader": "memory_update", "gold": UPDATE_GOLD,
     "actual": ["Alice现在住北京"], "classification": "correct", "score": 100},
    {"name": "update_not_applied", "grader": "memory_update", "gold": UPDATE_GOLD,
     "actual": ["Alice现在住上海"], "classification": "omission", "score": 0},
    {"name": "update_current_conflict", "grader": "memory_update", "gold": UPDATE_GOLD,
     "actual": ["Alice现在住上海", "Alice现在住北京"], "classification": "hallucination", "score": 0},
    {"name": "update_history_preserved", "grader": "memory_update", "gold": UPDATE_GOLD,
     "actual": ["Alice在1月住上海", "Alice现在住北京"], "classification": "correct", "score": 100},
]
