"""Protocol-independent evaluation asset and execution projections."""

import json
from src.apps.evaluation.formatters.payload import canonical_json, mask_sensitive
from src.apps.evaluation.selectors.version import current_version


def record_fields(record, fields):
    return json.loads(canonical_json(mask_sensitive({key: getattr(record, key) for key in fields})))


def dataset_record(record):
    return {**record_fields(record, ("id", "name", "task_type", "status", "description")),
            "published_version_no": current_version(record)}


def version_record(record):
    return record_fields(record, ("id", "dataset_id", "version_no", "version_label", "status", "content_hash", "schema_snapshot", "change_summary", "published_at"))


def item_record(record):
    return record_fields(record, ("id", "dataset_version_id", "input_data", "expected_output", "context", "metadata", "tags", "enabled", "weight", "priority", "content_hash", "grading_config", "scenario", "data_source"))


def case_record(record):
    from src.apps.evaluation.formatters.case_description import case_description
    return {**record_fields(record, ("id", "name", "project_product_id", "module_id", "dataset_version_id", "description", "status", "config")), "description": case_description(record)}


def case_summary(record):
    from src.apps.evaluation.formatters.case_description import case_description
    return {**record_fields(record, ("id", "name", "project_product_id", "module_id", "dataset_version_id", "description", "status")), "description": case_description(record)}


def execution_record(record):
    return record_fields(record, ("id", "case_id", "dataset_version_id", "execution_no", "test_env", "status", "verdict", "progress", "summary", "snapshot", "details", "retry_of_id", "started_at", "finished_at"))


def result_record(record):
    result = record_fields(record, ("id", "execution_id", "dataset_item_id", "repeat_index", "execution_status", "grade_status", "verdict", "score", "error_category", "item_snapshot", "resolved_expected_output", "actual_output", "details", "attempts"))
    result["grades"] = [record_fields(grade, ("grading_snapshot", "grader_key", "grader_version", "score", "raw_value", "passed", "reason", "evidence", "confidence")) for grade in record.grade_results.all()]
    return result
