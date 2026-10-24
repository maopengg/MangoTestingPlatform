from __future__ import annotations

from src.apps.auto_api.exceptions import API_VERSION_CASE_NOT_FOUND, AutoApiError
from src.apps.auto_api.models import ApiCase


class ApiCaseQueryService:
    @staticmethod
    def get_instance(case_id: int) -> ApiCase:
        try:
            return ApiCase.objects.select_related(
                "project_product",
                "project_product__project",
                "module",
                "case_people",
            ).get(id=case_id)
        except ApiCase.DoesNotExist as error:
            raise AutoApiError(
                API_VERSION_CASE_NOT_FOUND,
                value=(case_id,),
                details={"case_id": case_id},
            ) from error


__all__ = ["ApiCaseQueryService"]
