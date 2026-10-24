def format_pytest_case(instance):
    from src.apps.auto_pytest.api.serializers.pytest_case import PytestCaseSerializersC

    return PytestCaseSerializersC(instance=instance).data if instance is not None else None
