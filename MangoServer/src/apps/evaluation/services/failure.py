"""Keep unexpected runtime details in server logs, outside persisted responses."""

import logging
from src.apps.evaluation.exceptions import EVALUATION_EXECUTION_FAILED
from src.common.exceptions import MangoServerError


logger = logging.getLogger(__name__)


def failure_message(error):
    if isinstance(error, MangoServerError):
        return error.msg
    logger.error("Evaluation execution failed", exc_info=(type(error), error, error.__traceback__))
    return EVALUATION_EXECUTION_FAILED.message
