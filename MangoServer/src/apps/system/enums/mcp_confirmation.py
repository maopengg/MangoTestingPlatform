from src.common.enums.base import BaseEnum


class McpConfirmationStatusEnum(BaseEnum):
    ACCEPTED = ('accepted', 'Accepted')
    EXPIRED = ('PREVIEW_EXPIRED', 'Expired or missing')
    TEXT_MISMATCH = ('CONFIRM_TEXT_MISMATCH', 'Confirmation text mismatch')
