from src.apps.evaluation.exceptions import EVALUATION_EXECUTION_NOT_FOUND, EvaluationError
from src.apps.evaluation.selectors.case import get_case
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector


def case_executions(case_id, user):
    get_case(case_id, user)
    return EvaluationQuerySelector.executions(user, case_id)


def get_execution(case_id, execution_id, user):
    record = case_executions(case_id, user).filter(pk=execution_id).first()
    if record is None:
        raise EvaluationError(EVALUATION_EXECUTION_NOT_FOUND)
    return record
