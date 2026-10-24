from copy import deepcopy

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import transaction
from mangotools.mangos import get_execution_order_with_config_ids
from rest_framework import serializers

from src.apps.auto_ui.enums import DriveTypeEnum, ElementOperationEnum
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_DATA_SOURCE_DATA_SOURCE_REQUIRED,
    UI_DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID,
    UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED,
    UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_DELETE_NOT_FOUND,
    UI_SQL_ASSERTION_PROJECT_PRODUCT_SQL_DATA_SOURCE_ASSERTION_INVALID,
    UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_INVALID,
    UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_TYPE_UNSUPPORTED,
    UI_STEP_STEP_PAGE_NODE_INVALID,
    UI_STEP_STEP_PAGE_INVALID,
    UI_STEP_STEP_PAGE_CONFIG_INVALID,
    UI_STEP_STEP_PAGE_NOT_FOUND,
    UI_STEP_STEP_PAGE_CONFIG_INVALID_CODE_STEP_PAGE_CONFIG_INVALID,
)
from src.apps.auto_ui.models import PageSteps, PageStepsDetailed
from src.apps.auto_ui.schemas.case_schema import validate_flow_data
from src.apps.auto_ui.services.query_ope_key_name import get_by_object
from src.apps.system.enums import CacheDataKey2Enum
from src.apps.system.services.cache_data_value import CacheDataValue


class PageStepDetailMutationService:
    """页面步骤详情与 flow_data 的统一原子保存入口。"""

    METHOD_CACHE_KEYS = {
        "select_value": CacheDataKey2Enum.SELECT_VALUE.value,
    }
    MUTABLE_FIELDS = {
        "type",
        "ele_name",
        "step_sort",
        "ope_key",
        "ope_value",
        "sql_execute",
        "key_list",
        "sql",
        "custom",
        "key",
        "value",
        "condition_value",
        "func",
        "precondition",
        "postcondition",
    }

    @classmethod
    @transaction.atomic
    def save(
            cls,
            *,
            page_step_id: int,
            payload: dict,
            operator_id: int | None,
            detail_id: int | None = None,
            node_id: str | None = None,
            flow_data: dict | None = None,
            page_type: int | None = None,
    ) -> dict:
        page_step = PageSteps.objects.select_for_update().get(id=page_step_id)
        instance = None
        if detail_id is not None:
            instance = PageStepsDetailed.objects.select_for_update().filter(
                id=detail_id,
                page_step_id=page_step.id,
            ).first()
            if instance is None:
                raise AutoUiError(UI_STEP_STEP_PAGE_NOT_FOUND)

        normalized_payload = {
            key: payload.get(key)
            for key in cls.MUTABLE_FIELDS
            if key in (payload or {})
        }
        if instance is not None:
            current_payload = {
                field: getattr(instance, f"{field}_id", None)
                if field == "ele_name"
                else getattr(instance, field)
                for field in cls.MUTABLE_FIELDS
            }
            normalized_payload = {**current_payload, **normalized_payload}
        normalized_payload["page_step"] = page_step.id
        if operator_id is not None:
            normalized_payload["update_user"] = operator_id
        cls.validate_detail_payload(
            normalized_payload,
            page_type=page_type,
            project_product_id=page_step.project_product_id,
        )

        normalized_flow = None
        if instance is None and flow_data is None:
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=("创建详情时 flow_data 必填",))
        if flow_data is not None:
            normalized_flow = cls.normalize_flow_data(flow_data)
            if not node_id:
                raise AutoUiError(UI_STEP_STEP_PAGE_NODE_INVALID)

        detail = cls._save_detail(instance, normalized_payload)

        if normalized_flow is not None:
            matching_node = next(
                (
                    node
                    for node in normalized_flow["nodes"]
                    if node.get("id") == node_id
                ),
                None,
            )
            if matching_node is None:
                raise AutoUiError(UI_STEP_STEP_PAGE_NODE_INVALID)
            matching_node.setdefault("config", {})["id"] = detail.id
            cls.validate_flow_detail_references(page_step.id, normalized_flow)
            page_step.flow_data = normalized_flow

        if operator_id is not None:
            page_step.update_user_id = operator_id
        page_step.config_version += 1
        page_step.run_flow = cls.build_run_flow(
            page_step.flow_data,
            page_step_id=page_step.id,
        )
        update_fields = ["run_flow", "config_version", "update_time"]
        if normalized_flow is not None:
            update_fields.append("flow_data")
        if operator_id is not None:
            update_fields.append("update_user")
        page_step.save(update_fields=update_fields)
        return {
            "page_step_detail_id": detail.id,
            "page_step_id": page_step.id,
            "flow_data": page_step.flow_data,
            "run_flow": page_step.run_flow,
            **cls._serialize_detail(detail),
        }

    @classmethod
    @transaction.atomic
    def duplicate(
            cls,
            *,
            page_step_id: int,
            source_detail_id: int,
            node_id: str,
            flow_data: dict,
            operator_id: int | None,
    ) -> dict:
        page_step = PageSteps.objects.select_for_update().get(id=page_step_id)
        source = PageStepsDetailed.objects.select_for_update().filter(
            id=source_detail_id,
            page_step_id=page_step.id,
        ).first()
        if source is None:
            raise AutoUiError(UI_STEP_STEP_PAGE_NOT_FOUND)

        normalized_flow = cls.normalize_flow_data(flow_data)
        matching_node = next(
            (node for node in normalized_flow["nodes"] if node.get("id") == node_id),
            None,
        )
        if matching_node is None:
            raise AutoUiError(UI_STEP_STEP_PAGE_NODE_INVALID)

        detail = PageStepsDetailed.objects.create(
            page_step_id=page_step.id,
            update_user_id=operator_id,
            **cls.clone_detail_values(source),
        )
        matching_node.setdefault("config", {})["id"] = detail.id
        cls.validate_flow_detail_references(page_step.id, normalized_flow)
        page_step.flow_data = normalized_flow
        page_step.run_flow = cls.build_run_flow(
            normalized_flow,
            page_step_id=page_step.id,
        )
        if operator_id is not None:
            page_step.update_user_id = operator_id
        page_step.config_version += 1
        update_fields = ["flow_data", "run_flow", "config_version", "update_time"]
        if operator_id is not None:
            update_fields.append("update_user")
        page_step.save(update_fields=update_fields)
        return {
            "page_step_detail_id": detail.id,
            "page_step_id": page_step.id,
            "flow_data": page_step.flow_data,
            "run_flow": page_step.run_flow,
            **cls._serialize_detail(detail),
        }

    @staticmethod
    def _save_detail(instance: PageStepsDetailed | None, payload: dict) -> PageStepsDetailed:
        detail = instance or PageStepsDetailed()
        for name, value in payload.items():
            try:
                field = PageStepsDetailed._meta.get_field(name)
            except FieldDoesNotExist:
                continue
            setattr(detail, field.attname, value)
        try:
            detail.full_clean()
        except ValidationError as exc:
            errors = getattr(exc, "message_dict", None) or exc.messages
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=(errors,)) from exc
        detail.save()
        return detail

    @staticmethod
    def _serialize_detail(detail: PageStepsDetailed) -> dict:
        return {
            field.name: getattr(detail, field.attname)
            for field in detail._meta.concrete_fields
        }

    @classmethod
    def clone_detail_values(cls, source: PageStepsDetailed) -> dict:
        values = {}
        for field in cls.MUTABLE_FIELDS:
            target_field = "ele_name_id" if field == "ele_name" else field
            source_value = source.ele_name_id if field == "ele_name" else getattr(source, field, None)
            values[target_field] = deepcopy(source_value)
        return values

    @classmethod
    def refresh_run_flow(cls, page_step_id: int) -> str | None:
        page_step = PageSteps.objects.get(id=page_step_id)
        page_step.run_flow = cls.build_run_flow(
            page_step.flow_data,
            page_step_id=page_step.id,
        )
        page_step.config_version += 1
        page_step.save(update_fields=["run_flow", "config_version", "update_time"])
        return page_step.run_flow

    @classmethod
    def build_run_flow(
            cls,
            flow_data: dict | None,
            page_step_id: int | None = None,
    ) -> str | None:
        try:
            detail_ids = get_execution_order_with_config_ids(flow_data or {})
        except (KeyError, TypeError, ValueError):
            return None
        normalized_detail_ids = []
        for detail_id in detail_ids or []:
            if detail_id in (None, ""):
                continue
            try:
                normalized_detail_ids.append(int(detail_id))
            except (TypeError, ValueError):
                continue
        if not normalized_detail_ids:
            return None
        detail_filters = {"id__in": normalized_detail_ids}
        if page_step_id is not None:
            detail_filters["page_step_id"] = page_step_id
        details = PageStepsDetailed.objects.filter(
            **detail_filters
        ).select_related("ele_name")
        detail_map = {detail.id: detail for detail in details}
        if not detail_map:
            return None
        select_value = CacheDataValue.get_cache_value(
            key=CacheDataKey2Enum.SELECT_VALUE.value
        )
        labels = []
        for detail_id in normalized_detail_ids:
            detail = detail_map.get(detail_id)
            if detail is None:
                continue
            if detail.ele_name:
                labels.append(detail.ele_name.name)
            elif detail.ope_key:
                method = get_by_object(select_value or [], detail.ope_key)
                labels.append(detail.ope_key if method is None else method.get("label"))
            else:
                labels.append(ElementOperationEnum.get_value(detail.type))
        return f"->{'->'.join(str(label) for label in labels)}" if labels else None

    @classmethod
    def normalize_flow_data(cls, flow_data: dict) -> dict:
        try:
            normalized = validate_flow_data(flow_data)
        except serializers.ValidationError as error:
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=(error.detail,)) from error
        if not normalized.get("nodes"):
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=("nodes 不能为空",))
        return normalized

    @classmethod
    def validate_flow_detail_references(cls, page_step_id: int, flow_data: dict):
        detail_ids = {
            int(node["config"]["id"])
            for node in flow_data.get("nodes") or []
            if isinstance(node.get("config"), dict) and node["config"].get("id")
        }
        if not detail_ids:
            return
        matched = PageStepsDetailed.objects.filter(
            page_step_id=page_step_id,
            id__in=detail_ids,
        ).count()
        if matched != len(detail_ids):
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID_CODE_STEP_PAGE_CONFIG_INVALID)

    @classmethod
    def validate_detail_payload(
            cls,
            payload: dict,
            page_type: int | None = None,
            project_product_id: int | None = None,
    ):
        step_type = payload.get("type")
        if step_type not in ElementOperationEnum.get_key_list():
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("type 不属于 ElementOperationEnum",))
        if step_type in (
                ElementOperationEnum.OPE.value,
                ElementOperationEnum.ASS.value,
                ElementOperationEnum.CONDITION.value,
        ):
            kind = (
                "operation"
                if step_type == ElementOperationEnum.OPE.value
                else "assertion"
            )
            method = cls.find_method(
                cls.validation_method_tree(kind, page_type),
                payload.get("ope_key"),
            )
            if method is None:
                raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("ope_key 不属于 UI 方法树",))
            ope_value = payload.get("ope_value") or []
            if (
                    step_type == ElementOperationEnum.ASS.value
                    and str(payload.get("ope_key") or "").startswith("assert_sql_")
            ):
                cls.validate_sql_assertion_datasource(
                    ope_value,
                    project_product_id=project_product_id,
                )
                method = {
                    **method,
                    "parameter": [
                        *(method.get("parameter") or []),
                        {
                            "f": "datasource_alias",
                            "d": True,
                        },
                    ],
                }
            cls.validate_ope_value(
                method,
                ope_value,
                deferred_fields={"expect"}
                if step_type == ElementOperationEnum.CONDITION.value
                else None,
            )
        if step_type == ElementOperationEnum.SQL.value and not payload.get("sql_execute"):
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("SQL 步骤缺少 sql_execute",))
        if step_type == ElementOperationEnum.SQL.value:

            for index, item in enumerate(payload.get('sql_execute') or [], start=1):
                if not isinstance(item, dict) or not item.get('datasource_alias'):
                    raise AutoUiError(UI_DATA_SOURCE_DATA_SOURCE_REQUIRED, value=('页面步骤数据库操作', index))
                operation = item.get('sql')
                if operation in [None, ''] or (isinstance(operation, str) and not operation.strip()):
                    raise AutoUiError(UI_DATA_SOURCE_DATA_SOURCE_EXECUTION_INVALID, value=('页面步骤数据库操作', index))
        if step_type == ElementOperationEnum.CUSTOM.value and not payload.get("custom"):
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("自定义步骤缺少 custom",))
        if step_type == ElementOperationEnum.CONDITION.value:
            condition_value = payload.get("condition_value")
            if condition_value is not None and (
                    not isinstance(condition_value, dict)
                    or "expect" not in condition_value
            ):
                raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("condition_value 必须包含 expect",))
        if step_type == ElementOperationEnum.PYTHON_CODE.value and not payload.get("func"):
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("Python 步骤缺少 func",))
        if step_type == ElementOperationEnum.FORCE_WAIT.value:
            ope_value = payload.get("ope_value") or []
            seconds_item = next(
                (
                    item for item in ope_value
                    if isinstance(item, dict) and item.get("f") == "seconds"
                ),
                None,
            )
            try:
                seconds = float(seconds_item.get("v")) if seconds_item else None
            except (TypeError, ValueError):
                seconds = None
            if seconds is None or seconds < 0 or seconds > 3600:
                raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID,
                                  value=("强制等待时长必须在 0 到 3600 秒之间",),
                                  )

    @classmethod
    def validation_method_tree(
            cls,
            kind: str,
            page_type: int | None = None,
    ) -> list:
        return cls.method_tree(kind, page_type)

    @classmethod
    def method_tree(cls, kind: str, page_type: int | None = None) -> list:
        method_tree = cls.cache_method_tree(cls.METHOD_CACHE_KEYS["select_value"])
        operation_groups = {"web", "android", "ios"}
        client_assertion_groups = {"ass_web", "ass_android", "ass_ios"}
        shared_assertions = [
            item
            for item in method_tree
            if isinstance(item, dict)
               and item.get("value") not in operation_groups | client_assertion_groups
        ]

        if kind == "operation":
            if page_type is None:
                return [
                    item
                    for item in method_tree
                    if isinstance(item, dict) and item.get("value") in operation_groups
                ]
            group_value = (
                "web"
                if int(page_type) == DriveTypeEnum.WEB.value
                else "android"
                if int(page_type) == DriveTypeEnum.ANDROID.value
                else "ios"
                if int(page_type) == DriveTypeEnum.IOS.value
                else None
            )
            group = next(
                (
                    item
                    for item in method_tree
                    if isinstance(item, dict) and item.get("value") == group_value
                ),
                None,
            )
            return list(group.get("children") or []) if group else []
        if kind in ("assertion", "public_assertion"):
            if kind == "public_assertion":
                return shared_assertions
            group_value = (
                "ass_web"
                if int(page_type) == DriveTypeEnum.WEB.value
                else "ass_android"
                if int(page_type) == DriveTypeEnum.ANDROID.value
                else "ass_ios"
                if int(page_type) == DriveTypeEnum.IOS.value
                else None
            ) if page_type is not None else None
            data = []
            for item in method_tree:
                if not isinstance(item, dict):
                    continue
                value = item.get("value")
                if value in operation_groups:
                    continue
                if value in client_assertion_groups:
                    if group_value is None or value == group_value:
                        data.extend(item.get("children") or [])
                    continue
            data.extend(shared_assertions)
            return data
        return []

    @staticmethod
    def cache_method_tree(key: str) -> list:
        data = CacheDataValue.get_cache_value(key=key)
        return data if isinstance(data, list) else []

    @classmethod
    def find_method(cls, method_tree: list, method_value: str | None) -> dict | None:
        if not method_value:
            return None
        for item in method_tree or []:
            if not isinstance(item, dict):
                continue
            if item.get("value") == method_value:
                return item
            found = cls.find_method(item.get("children") or [], method_value)
            if found:
                return found
        return None

    @classmethod
    def validate_ope_value(
            cls,
            method: dict,
            ope_value: list | None,
            deferred_fields: set[str] | None = None,
    ):
        expected = method.get("parameter") or []
        actual = ope_value or []
        deferred_fields = deferred_fields or set()
        actual_by_field = {
            item.get("f"): item
            for item in actual
            if isinstance(item, dict)
        }
        expected_fields = {
            item.get("f")
            for item in expected
            if isinstance(item, dict)
        }
        unexpected = [
            item.get("f")
            for item in actual
            if isinstance(item, dict) and item.get("f") not in expected_fields
        ]
        if unexpected:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID,
                              value=(f"ope_value 包含未知参数：{unexpected}",),
                              )
        for item in expected:
            if not isinstance(item, dict) or item.get("d") is not True:
                continue
            field = item.get("f")
            if field in deferred_fields:
                continue
            if (
                    field not in actual_by_field
                    or actual_by_field[field].get("v") in (None, "")
            ):
                raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID,
                                  value=(f"ope_value 缺少必填参数：{field}",),
                                  )

    @staticmethod
    def validate_sql_assertion_datasource(
            ope_value: list | None,
            *,
            project_product_id: int | None,
    ):
        from src.apps.data_factory.models import DataFactoryDatasourceAlias
        from src.apps.data_factory.services.data_source_execution import (
            DataSourceExecutionService,
        )
        from src.apps.test_center.enums.data_source import DataSourceTypeEnum
        from mangotools.enums import StatusEnum

        values = {
            item.get("f"): item.get("v")
            for item in ope_value or []
            if isinstance(item, dict)
        }
        datasource_alias_id = values.get("datasource_alias")
        if datasource_alias_id in (None, ""):
            raise AutoUiError(UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_REQUIRED)
        alias = DataFactoryDatasourceAlias.objects.filter(
            id=datasource_alias_id,
        ).first()
        if alias is None:
            raise AutoUiError(UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_DELETE_NOT_FOUND)
        if project_product_id is not None and alias.project_product_id != project_product_id:
            raise AutoUiError(UI_SQL_ASSERTION_PROJECT_PRODUCT_SQL_DATA_SOURCE_ASSERTION_INVALID)
        if alias.status != StatusEnum.SUCCESS.value:
            raise AutoUiError(UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_INVALID)
        if alias.db_type not in DataSourceExecutionService.EXECUTABLE_RELATIONAL_TYPES:
            type_name = DataSourceTypeEnum.obj().get(alias.db_type, alias.db_type)
            raise AutoUiError(UI_SQL_ASSERTION_SQL_DATA_SOURCE_ASSERTION_TYPE_UNSUPPORTED, value=(type_name,))
