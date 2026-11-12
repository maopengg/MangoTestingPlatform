"""Update one execution detail group while preserving the other groups."""

from src.apps.evaluation.schemas.detail import EvaluationItemDetails


_UNSET = object()


def update_item_details(item_result, *, references=None, timing=None, error_message=_UNSET):
    payload = EvaluationItemDetails.model_validate(item_result.details or {}).model_dump(mode="json")
    if references is not None:
        payload["references"] = {**payload["references"], **references}
    if timing is not None:
        payload["timing"] = {**payload["timing"], **timing}
    if error_message is not _UNSET:
        payload["error_message"] = error_message
    item_result.details = EvaluationItemDetails.model_validate(payload).model_dump(mode="json")
