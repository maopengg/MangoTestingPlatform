from src.apps.evaluation.exceptions import EVALUATION_DATASET_VERSION_NOT_FOUND, EvaluationError
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.selectors.scope import ensure_dataset_access


def get_dataset_version(version_id, user):
    version = EvaluationQuerySelector.dataset_versions().filter(id=version_id).first()
    if version is None:
        raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
    ensure_dataset_access(user)
    return version


def version_diff(current, baseline):
    if current.dataset_id != baseline.dataset_id:
        raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
    current_rows = dict(current.items.values_list("id", "content_hash"))
    baseline_rows = dict(baseline.items.values_list("id", "content_hash"))
    return {
        "current_version_id": current.id,
        "baseline_version_id": baseline.id,
        "added": sorted(current_rows.keys() - baseline_rows.keys()),
        "removed": sorted(baseline_rows.keys() - current_rows.keys()),
        "changed": sorted(key for key in current_rows.keys() & baseline_rows.keys() if current_rows[key] != baseline_rows[key]),
        "schema_changed": current.schema_snapshot != baseline.schema_snapshot,
    }
