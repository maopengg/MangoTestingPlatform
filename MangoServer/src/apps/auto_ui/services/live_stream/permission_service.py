from src.apps.auto_ui.enums.live_stream import LiveStreamExecutionType
from src.apps.auto_ui.exceptions import (
    AUTO_UI_LIVE_STREAM_PERMISSION_SERVICE_EXECUTION_NOT_FOUND,
    AUTO_UI_LIVE_STREAM_PERMISSION_SERVICE_TYPE_EXECUTION_UNSUPPORTED,
    AutoUiError,
)
from src.apps.auto_ui.models import Page, PageSteps, UiCase


class LiveStreamPermissionService:
    @classmethod
    def validate_execution(cls, execution_type: str, execution_id: str) -> None:
        if execution_type == LiveStreamExecutionType.UI_CASE.value:
            exists = UiCase.objects.filter(id=execution_id).exists()
        elif execution_type == LiveStreamExecutionType.PAGE_STEP_DEBUG.value:
            exists = PageSteps.objects.filter(id=execution_id).exists()
        elif execution_type == LiveStreamExecutionType.ELEMENT_CHECK.value:
            exists = Page.objects.filter(id=execution_id).exists()
        elif execution_type == LiveStreamExecutionType.ELEMENT_WORKSPACE.value:
            exists = Page.objects.filter(id=execution_id).exists()
        elif execution_type == LiveStreamExecutionType.PAGE_STEP_WORKSPACE.value:
            exists = PageSteps.objects.filter(id=execution_id).exists()
        else:
            raise AutoUiError(AUTO_UI_LIVE_STREAM_PERMISSION_SERVICE_TYPE_EXECUTION_UNSUPPORTED)
        if not exists:
            raise AutoUiError(AUTO_UI_LIVE_STREAM_PERMISSION_SERVICE_EXECUTION_NOT_FOUND)
