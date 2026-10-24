"""Pytest 资产写入服务。"""

from src.apps.auto_pytest.exceptions import AutoPytestError
from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.common.database import ModelMutationValidationError, model_payload, save_model
from src.common.exceptions import UPDATE_VALIDATION_FAILED


class PytestAssetMutationService:
    @staticmethod
    def update_product(product_id: int, payload: dict, *, operator_id: int | None = None) -> dict:
        instance = PytestProduct.objects.get(id=product_id)
        data = dict(payload)
        if operator_id is not None:
            data["update_user"] = operator_id
        try:
            return model_payload(save_model(PytestProduct, data, instance=instance, partial=True))
        except ModelMutationValidationError as error:
            raise AutoPytestError(UPDATE_VALIDATION_FAILED, value=(error.errors,)) from error

    @staticmethod
    def delete_case(case_id: int) -> None:
        PytestCase.objects.get(id=case_id).delete()

    @staticmethod
    def delete_product(product_id: int) -> None:
        PytestProduct.objects.get(id=product_id).delete()
