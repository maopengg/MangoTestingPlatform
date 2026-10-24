from src.apps.evaluation.exceptions import EVALUATION_OBJECT_NOT_FOUND, EvaluationError
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.selectors.scope import ensure_dataset_access


def get_dataset_item(dataset_item_id, user):
    dataset_item = EvaluationQuerySelector.items().filter(id=dataset_item_id).first()
    if dataset_item is None:
        raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
    ensure_dataset_access(user)
    return dataset_item
