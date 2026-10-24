def format_ui_case(instance):
    from src.apps.auto_ui.api.serializers.ui_case import UiCaseSerializersC

    return UiCaseSerializersC(instance=instance).data if instance is not None else None
