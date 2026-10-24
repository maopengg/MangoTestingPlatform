from src.apps.functional_test.models import (
    FunctionalTestContextResource,
    FunctionalTestPlan,
    ManualTestAutomationBinding,
    ManualTestCase,
    ManualTestSuite,
)


class FunctionalTestQuerySelector:
    @staticmethod
    def functional_test_context_resource():
        return FunctionalTestContextResource.objects.all()

    @staticmethod
    def functional_test_plan():
        return FunctionalTestPlan.objects.all()

    @staticmethod
    def manual_test_automation_binding():
        return ManualTestAutomationBinding.objects.all()

    @staticmethod
    def manual_test_case():
        return ManualTestCase.objects.all()

    @staticmethod
    def manual_test_suite():
        return ManualTestSuite.objects.all()
