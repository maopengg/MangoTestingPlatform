from src.apps.auto_pytest.models import (
    PytestCase,
    PytestProduct,
    PytestRepository,
)


class PytestQuerySelector:
    @staticmethod
    def pytest_case():
        return PytestCase.objects.all()

    @staticmethod
    def pytest_product():
        return PytestProduct.objects.all()

    @staticmethod
    def pytest_repository():
        return PytestRepository.objects.all()
