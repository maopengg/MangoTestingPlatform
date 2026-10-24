from src.apps.auto_ui.models import (
    Page,
    PageElement,
    PageSteps,
    PageStepsDetailed,
    UiAuthConfig,
    UiCase,
    UiCaseStepsDetailed,
    UiPublic,
)


class UiQuerySelector:
    @staticmethod
    def page():
        return Page.objects.all()

    @staticmethod
    def page_element():
        return PageElement.objects.all()

    @staticmethod
    def page_steps():
        return PageSteps.objects.all()

    @staticmethod
    def page_steps_detailed():
        return PageStepsDetailed.objects.all()

    @staticmethod
    def ui_auth_config():
        return UiAuthConfig.objects.all()

    @staticmethod
    def ui_case():
        return UiCase.objects.all()

    @staticmethod
    def ui_case_steps_detailed():
        return UiCaseStepsDetailed.objects.all()

    @staticmethod
    def ui_public():
        return UiPublic.objects.all()


class UiModelQuerySelector:
    @staticmethod
    def by_id(model, item_id: int):
        return model.objects.filter(id=item_id).first()
