"""Resolve an immutable interface's normalized HTTP contract."""

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService


def fixed_interface_contract(api_info_id, revision_id=None, release_id=None):
    if revision_id is None:
        revision_id = ApiQuerySelector.api_info_release().filter(id=release_id, api_info_id=api_info_id).values_list("revision_id", flat=True).first()
    revision = ApiQuerySelector.api_info_revision().filter(id=revision_id, api_info_id=api_info_id).first()
    if revision is None:
        return None
    return {"checksum": revision.checksum, "config": ApiInfoRuntimeService.normalize_payload(revision.payload)}
