from .version_parts.editing import ApiCaseRevisionEditingMixin
from .version_parts.impact import ApiCaseRevisionImpactMixin
from .version_parts.loading import ApiCaseRevisionLoadingMixin
from .version_parts.recording import ApiCaseRevisionRecordingMixin
from .version_parts.selection import ApiCaseRevisionSelectionMixin


class ApiCaseRevisionService(ApiCaseRevisionRecordingMixin, ApiCaseRevisionImpactMixin, ApiCaseRevisionEditingMixin,
                             ApiCaseRevisionSelectionMixin, ApiCaseRevisionLoadingMixin):
    BATCH_EXECUTION_EDITING = 'editing'
    BATCH_EXECUTION_PUBLISHED = 'published'
    PUBLICATION_UNPUBLISHED = 'unpublished'
    PUBLICATION_PREPUBLISHED = 'prepublished'
    PUBLICATION_PUBLISHED = 'published'
