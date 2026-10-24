from src.apps.evaluation.exceptions import EVALUATION_OBJECT_NOT_FOUND, EvaluationError
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector


def get_case(case_id, user):
    case = EvaluationQuerySelector.cases(user).filter(pk=case_id).first()
    if case is None:
        raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
    return case
