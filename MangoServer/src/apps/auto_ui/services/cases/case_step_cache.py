import hashlib
import json

from django.db import transaction
from mangotools.contracts import UiStepDataContract
from mangotools.mangos import get_execution_order_with_config_ids

from src.apps.auto_ui.enums import ElementOperationEnum
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_STEP_STEP_PAGE_INVALID,
    UI_STEP_CACHE_STEP_NOT_FOUND,
    UI_STEP_STEP_PAGE_TYPE_UNSUPPORTED,
)
from src.apps.auto_ui.models import PageStepsDetailed, UiCaseStepsDetailed


class UiCaseStepCacheService:
    """严格按照页面流程图顺序生成 UI Case step 的执行缓存。"""

    SOURCE_MD5_KEY = "_source_md5"
    EDITABLE_CASE_FIELDS = {"page_step_details_data"}

    @classmethod
    @transaction.atomic
    def refresh(
            cls,
            *,
            case_step_id: int | None = None,
            case_id: int | None = None,
            operator_id: int | None = None,
    ) -> dict:
        if case_step_id is not None:
            targets = UiCaseStepsDetailed.objects.select_for_update().filter(
                id=case_step_id
            )
        elif case_id is not None:
            targets = UiCaseStepsDetailed.objects.select_for_update().filter(
                case_id=case_id
            )
        else:
            raise AutoUiError(UI_STEP_CACHE_STEP_NOT_FOUND)
        targets = list(targets.select_related("page_step"))
        if not targets:
            raise AutoUiError(UI_STEP_CACHE_STEP_NOT_FOUND)

        updated = []
        for case_step in targets:
            source_case_data = cls.build_case_data(case_step)
            case_data, sync_summary = cls.merge_case_data(
                case_step.case_data,
                source_case_data,
            )
            case_step.case_data = case_data
            update_fields = ["case_data", "update_time"]
            if operator_id is not None:
                case_step.update_user_id = operator_id
                update_fields.append("update_user")
            case_step.save(update_fields=update_fields)
            updated.append(
                {
                    "case_step_id": case_step.id,
                    "case_data_count": len(case_data),
                    **sync_summary,
                }
            )
        return {"updated": updated}

    @classmethod
    def merge_case_data(
            cls,
            current_case_data: list[dict] | None,
            source_case_data: list[dict],
    ) -> tuple[list[dict], dict]:
        """按页面步骤节点来源指纹同步，并保留未变化节点的 Case 入参。"""
        current_items = [
            item for item in (current_case_data or []) if isinstance(item, dict)
        ]
        current_map = {
            str(item.get("page_step_details_id")): item
            for item in current_items
            if item.get("page_step_details_id") not in (None, "")
        }
        source_ids = {
            str(item["page_step_details_id"])
            for item in source_case_data
        }
        summary = {
            "added_count": 0,
            "updated_count": 0,
            "unchanged_count": 0,
            "removed_count": sum(
                1
                for item_id in current_map
                if item_id not in source_ids
            ),
            "initialized_count": 0,
        }
        merged = []
        for source_item in source_case_data:
            item_id = str(source_item["page_step_details_id"])
            current_item = current_map.get(item_id)
            if current_item is None:
                merged.append(source_item)
                summary["added_count"] += 1
                continue

            source_md5 = source_item[cls.SOURCE_MD5_KEY]
            current_md5 = current_item.get(cls.SOURCE_MD5_KEY)
            if current_md5 == source_md5:
                merged.append(current_item)
                summary["unchanged_count"] += 1
                continue
            if current_md5:
                merged.append(source_item)
                summary["updated_count"] += 1
                continue

            # 历史缓存没有来源指纹，无法区分入参差异来自 Case 覆盖还是页面步骤变更。
            # 首次升级同步优先保留 Case 数据；若节点结构已变化，则仍同步最新来源节点。
            if cls._same_source_structure(current_item, source_item):
                initialized_item = dict(current_item)
                initialized_item[cls.SOURCE_MD5_KEY] = source_md5
                merged.append(initialized_item)
                summary["initialized_count"] += 1
            else:
                merged.append(source_item)
                summary["updated_count"] += 1
        return merged, summary

    @classmethod
    def _same_source_structure(cls, current_item: dict, source_item: dict) -> bool:
        ignored_fields = cls.EDITABLE_CASE_FIELDS | {cls.SOURCE_MD5_KEY}
        current_structure = {
            key: value
            for key, value in current_item.items()
            if key not in ignored_fields
        }
        source_structure = {
            key: value
            for key, value in source_item.items()
            if key not in ignored_fields
        }
        return current_structure == source_structure

    @classmethod
    def source_md5(cls, item: dict) -> str:
        payload = {
            key: value
            for key, value in item.items()
            if key != cls.SOURCE_MD5_KEY
        }
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def build_case_data(cls, case_step: UiCaseStepsDetailed) -> list[dict]:
        flow_data = case_step.page_step.flow_data if case_step.page_step else None
        if not isinstance(flow_data, dict) or not flow_data.get("nodes"):
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=("nodes 不能为空",))
        try:
            detail_ids = [
                int(detail_id)
                for detail_id in get_execution_order_with_config_ids(flow_data)
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=(str(error),)) from error
        if not detail_ids or len(set(detail_ids)) != len(detail_ids):
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=("流程图详情 ID 无效或重复",))

        details = PageStepsDetailed.objects.filter(
            page_step_id=case_step.page_step_id,
            id__in=detail_ids,
        ).select_related("ele_name")
        detail_map = {detail.id: detail for detail in details}
        missing_ids = [
            detail_id
            for detail_id in detail_ids
            if detail_id not in detail_map
        ]
        if missing_ids:
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=(f"详情不存在：{missing_ids}",))
        return [
            cls.serialize_detail(detail_map[detail_id])
            for detail_id in detail_ids
        ]

    @classmethod
    def serialize_detail(cls, detail: PageStepsDetailed) -> dict:
        if detail.type in (
                ElementOperationEnum.OPE.value,
                ElementOperationEnum.ASS.value,
                ElementOperationEnum.CONDITION.value,
                ElementOperationEnum.FORCE_WAIT.value,
        ):
            detail_data = detail.ope_value
        elif detail.type == ElementOperationEnum.SQL.value:
            detail_data = detail.sql_execute
        elif detail.type == ElementOperationEnum.CUSTOM.value:
            detail_data = detail.custom
        elif detail.type == ElementOperationEnum.PYTHON_CODE.value:
            detail_data = [{"func": detail.func}]
        else:
            raise AutoUiError(UI_STEP_STEP_PAGE_TYPE_UNSUPPORTED, value=(detail.type,))
        result = UiStepDataContract(
            type=detail.type,
            ope_key=detail.ope_key,
            page_step_details_id=detail.id,
            page_step_details_name=(
                detail.ele_name.name
                if detail.ele_name
                else None
            ),
            condition_value=detail.condition_value,
            page_step_details_data=detail_data,
        ).model_dump()
        result[cls.SOURCE_MD5_KEY] = cls.source_md5(result)
        return result
