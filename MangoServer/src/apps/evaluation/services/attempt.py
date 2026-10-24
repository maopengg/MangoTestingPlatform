"""Persist attempt history with its owning dataset_item result under a row lock."""

from django.db import transaction
from django.utils import timezone
from src.apps.evaluation.enums import EvaluationExecutionStatusEnum
from src.apps.evaluation.exceptions import EVALUATION_ATTEMPT_NOT_FOUND, EvaluationError
from src.apps.evaluation.models import EvaluationItemResult
from src.apps.evaluation.schemas.attempt import EvaluationAttemptRecord


class EvaluationAttemptService:
    @staticmethod
    @transaction.atomic
    def start(item_result):
        current = EvaluationItemResult.objects.select_for_update().get(pk=item_result.pk)
        history = list(current.attempts)
        now = timezone.now()
        record = EvaluationAttemptRecord(
            attempt_no=max((item["attempt_no"] for item in history), default=0) + 1,
            status=EvaluationExecutionStatusEnum.RUNNING,
            create_time=now, update_time=now,
        ).model_dump(mode="json")
        history.append(record)
        current.attempts = history
        current.save(update_fields=["attempts", "update_time"])
        item_result.attempts = history
        return record["attempt_no"]

    @staticmethod
    @transaction.atomic
    def finish(item_result, attempt_no, **changes):
        current = EvaluationItemResult.objects.select_for_update().get(pk=item_result.pk)
        history = list(current.attempts)
        for index, record in enumerate(history):
            if record["attempt_no"] == attempt_no:
                history[index] = EvaluationAttemptRecord.model_validate({
                    **record, **changes, "update_time": timezone.now(),
                }).model_dump(mode="json")
                break
        else:
            raise EvaluationError(EVALUATION_ATTEMPT_NOT_FOUND)
        current.attempts = history
        current.save(update_fields=["attempts", "update_time"])
        item_result.attempts = history
