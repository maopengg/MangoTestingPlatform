# -*- coding: utf-8 -*-

from __future__ import annotations

import re

from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import DataFactoryEntityStatusChangeSourceEnum
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_CONFIG_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryDatasourceBinding,
    DataFactoryEntity,
    DataFactoryField,
)
from src.apps.data_factory.services.datasource import DataFactoryDatasource, DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.data_factory.services.entity import DataFactoryEntityService
from src.apps.system.services.system_config import SystemConfigService
from src.apps.test_center.enums.data_source import DataSourceTypeEnum
from src.common.logging import log


class DataFactorySchemaMonitorService:
    """检测数据工厂实体字段规则与已绑定 MySQL 表结构是否一致。"""

    BULK_DISABLE_MIN_SCANNED_COUNT = 10
    BULK_DISABLE_MAX_COUNT = 10
    BULK_DISABLE_MAX_RATIO = 0.2

    SIGNATURE_FIELDS = (
        "name",
        "db_type",
        "nullable",
        "primary_key",
        "autoincrement",
        "max_length",
    )

    @staticmethod
    def binding_environment(binding) -> int | None:
        return binding.environment

    @classmethod
    def configured_validation_environments(cls) -> list[int] | None:
        return SystemConfigService.get_data_factory_validation_environments()

    @classmethod
    def filter_validation_bindings(cls, bindings: list) -> list:
        environments = cls.configured_validation_environments()
        if environments is None:
            return bindings
        environment_set = set(environments)
        return [
            binding for binding in bindings
            if cls.binding_environment(binding) in environment_set
        ]

    @classmethod
    def validate_entity_activation(cls, entity_id: int) -> dict:
        """启用前按系统配置选择环境，并以真实表结构为准进行严格校验。"""
        entity = DataFactoryEntity.objects.select_related("datasource_alias").get(id=entity_id)
        if not entity.datasource_alias_id:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(entity.name, "未绑定逻辑数据库"))
        if entity.datasource_alias.status != StatusEnum.SUCCESS.value:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(entity.name, "逻辑数据库已停用"))

        all_bindings = list(
            DataFactoryDatasourceBinding.objects.select_related(
                "database", "datasource_alias",
            ).filter(datasource_alias_id=entity.datasource_alias_id).order_by("id")
        )
        if not all_bindings:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(entity.name, "没有可校验的环境数据源绑定"))
        bindings = cls.filter_validation_bindings(all_bindings)
        if not bindings:
            environments = cls.configured_validation_environments() or []
            environment_text = "、".join(str(item) for item in environments)
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID,
                                   value=(entity.name, f"配置的校验环境（{environment_text}）没有数据源绑定"),
                                   )

        expected = cls.entity_signature(entity.id)
        if not expected:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(entity.name, "实体字段规则为空，请先同步表结构"))
        checked_bindings = []
        failures = []
        for binding in bindings:
            environment = cls.binding_environment(binding)
            try:
                DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
                schema = DataFactoryDiscover.get_table_schema(
                    DatasourceTargetService.resolve(binding, schema_name=entity.schema_name), entity.table_name)
                actual = cls.columns_signature(schema.get("columns") or [])
                differences = cls.describe_differences(expected, actual)
                differences.extend(cls.describe_key_differences(entity, schema))
                if differences:
                    failures.append({
                        "binding_id": binding.id,
                        "database_id": binding.database_id,
                        "environment": environment,
                        "differences": differences,
                    })
                else:
                    checked_bindings.append(binding.id)
            except Exception as error:
                failures.append({
                    "binding_id": binding.id,
                    "database_id": binding.database_id,
                    "environment": environment,
                    "error": DataFactoryDatasource._safe_error(binding.database, error),
                })
        if failures:
            first = failures[0]
            if first.get("differences"):
                fields = "、".join(item["field"] for item in first["differences"][:5])
                detail = f"环境 {first.get('environment')} 的表结构与实体字段不一致，涉及字段：{fields}"
            else:
                detail = f"环境 {first.get('environment')} 校验失败：{first.get('error')}"
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=(entity.name, detail))
        return {
            "entity_id": entity.id,
            "checked_binding_ids": checked_bindings,
            "checked_binding_count": len(checked_bindings),
        }

    @staticmethod
    def describe_key_differences(entity, schema: dict) -> list[dict]:
        """校验清理定位字段与数据库真实约束，避免数据创建后无法安全清理。"""
        columns = schema.get("columns") or []
        actual_primary_keys = schema.get("primary_keys")
        if actual_primary_keys is None:
            actual_primary_keys = [
                column.get("name")
                for column in columns
                if column.get("primary_key")
            ]
        actual_primary_keys = [str(item) for item in actual_primary_keys if item]
        configured_primary_key = str(getattr(entity, "primary_key", "") or "")
        differences = []
        if len(actual_primary_keys) != 1 or configured_primary_key != actual_primary_keys[0]:
            actual_text = "、".join(actual_primary_keys) or "未发现主键"
            differences.append({
                "field": "清理主键",
                "expected": configured_primary_key or "未配置",
                "actual": actual_text,
            })

        configured_unique_key = str(getattr(entity, "unique_key", "") or "")
        if configured_unique_key:
            single_unique_columns = {
                str(index["column_names"][0])
                for index in (schema.get("indexes") or [])
                if index.get("unique") and len(index.get("column_names") or []) == 1
            }
            single_unique_columns.update(actual_primary_keys)
            if configured_unique_key not in single_unique_columns:
                differences.append({
                    "field": "唯一键",
                    "expected": configured_unique_key,
                    "actual": "、".join(sorted(single_unique_columns)) or "未发现单列唯一约束",
                })
        return differences

    @staticmethod
    def _record_workbench_todo(entity, *, differences, invalidated_template_count, review_only=False):
        """待办是旁路提醒，写入失败不能中断结构扫描和实体保护。"""
        try:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService

            WorkbenchTodoService.record_data_factory_schema_issue(
                entity,
                differences=differences,
                invalidated_template_count=invalidated_template_count,
                review_only=review_only,
            )
        except Exception as error:
            log.system.error(
                f'记录数据工厂结构风险待办失败，entity_id={entity.id}，错误：{error}'
            )

    @staticmethod
    def _reconcile_workbench_reviews(scanned_entity_ids: set[int], active_entity_ids: set[int]):
        """仅使用扫描结论关闭待确认风险，扫描失败的实体不会被误判为已恢复。"""
        try:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService

            WorkbenchTodoService.resolve_data_factory_review_todos(
                scanned_entity_ids=scanned_entity_ids,
                active_entity_ids=active_entity_ids,
            )
        except Exception as error:
            log.system.error(f'同步数据工厂结构风险待办状态失败，错误：{error}')

    @classmethod
    def scan(cls, source_record_id: int | None = None) -> dict:
        entities = list(DataFactoryEntity.objects.select_related("datasource_alias").filter(
            status=StatusEnum.SUCCESS.value,
            datasource_alias__status=StatusEnum.SUCCESS.value,
            datasource_alias__db_type=DataSourceTypeEnum.MYSQL.value,
        ))
        result = {
            "scanned_entity_count": len(entities),
            "scanned_database_count": 0,
            "scanned_binding_count": 0,
            "observed_changed_entity_count": 0,
            "detected_changed_entity_count": 0,
            "changed_entity_count": 0,
            "invalidated_template_count": 0,
            "failed_binding_count": 0,
            "auto_disable_blocked": False,
            "safety_message": "",
            "changed_entities": [],
            "errors": [],
        }
        if not entities:
            return result
        entities_by_alias: dict[int, list[DataFactoryEntity]] = {}
        for entity in entities:
            entities_by_alias.setdefault(entity.datasource_alias_id, []).append(entity)
        bindings = list(DataFactoryDatasourceBinding.objects.select_related("database").filter(
            datasource_alias_id__in=entities_by_alias,
            database__db_type=DataSourceTypeEnum.MYSQL.value,
        ))
        bindings = cls.filter_validation_bindings(bindings)
        targets_by_database: dict[int, dict[int, dict]] = {}
        databases = {}
        for binding in bindings:
            try:
                database = DatasourceTargetService.for_metadata(binding)
            except DataFactoryError as error:
                result["failed_binding_count"] += len(entities_by_alias.get(binding.datasource_alias_id, []))
                result["errors"].append({"database_id": binding.database_id, "binding_id": binding.id,
                                         "error": DataFactoryDatasource._safe_error(binding.database, error)})
                continue
            databases[database.cache_key] = database
            for entity in entities_by_alias.get(binding.datasource_alias_id, []):
                target = targets_by_database.setdefault(database.cache_key, {}).setdefault(
                    entity.id,
                    {"entity": entity, "binding_ids": set()},
                )
                target["binding_ids"].add(binding.id)
                result["scanned_binding_count"] += 1

        expected_signatures = cls.entity_signatures([entity.id for entity in entities])
        changed_entities: dict[int, dict] = {}
        observed_changed_entity_ids = set()
        scanned_entity_ids = {
            entity_id
            for targets in targets_by_database.values()
            for entity_id in targets
        }
        failed_entity_ids = set()
        for target_key, targets in targets_by_database.items():
            database = databases[target_key]
            database_id = database.id
            result["scanned_database_count"] += 1
            try:
                schemas = DataFactoryDiscover.get_mysql_table_schemas(
                    database,
                    [target["entity"].table_name for target in targets.values()],
                )
            except Exception as error:
                failed_entity_ids.update(targets)
                failed_count = sum(len(target["binding_ids"]) for target in targets.values())
                result["failed_binding_count"] += failed_count
                result["errors"].append({
                    "database_id": database_id,
                    "entity_ids": sorted(targets),
                    "error": DataFactoryDatasource._safe_error(database, error),
                })
                continue
            for entity_id, target in targets.items():
                entity = target["entity"]
                schema = schemas.get(entity.table_name)
                actual = cls.columns_signature(schema.get("columns") or []) if schema else None
                if actual == expected_signatures[entity_id]:
                    continue
                observed_changed_entity_ids.add(entity_id)
                differences = cls.describe_incompatible_differences(
                    expected_signatures[entity_id],
                    actual,
                    schema.get("columns") or [] if schema else [],
                )
                if not differences:
                    continue
                changed = changed_entities.setdefault(
                    entity_id,
                    {"entity": entity, "binding_ids": set(), "differences": []},
                )
                changed["binding_ids"].update(target["binding_ids"])
                changed["differences"].append({
                    "database_id": database_id,
                    "items": differences,
                })

        result["observed_changed_entity_count"] = len(observed_changed_entity_ids)
        result["detected_changed_entity_count"] = len(changed_entities)
        conclusive_entity_ids = scanned_entity_ids - failed_entity_ids
        if cls.should_block_auto_disable(len(entities), len(changed_entities)):
            result["auto_disable_blocked"] = True
            result["safety_message"] = (
                f"本次扫描发现 {len(changed_entities)}/{len(entities)} 个实体结构存在差异，"
                "已触发批量保护，未自动停用任何实体，请先检查扫描口径或数据库变更范围。"
            )
            for changed in changed_entities.values():
                entity = changed["entity"]
                cls._record_workbench_todo(
                    entity,
                    differences=changed["differences"],
                    invalidated_template_count=0,
                    review_only=True,
                )
                result["changed_entities"].append({
                    "entity_id": entity.id,
                    "entity_name": entity.name,
                    "table_name": entity.table_name,
                    "binding_ids": sorted(changed["binding_ids"]),
                    "invalidated_template_count": 0,
                    "differences": changed["differences"],
                })
            cls._reconcile_workbench_reviews(
                conclusive_entity_ids,
                set(changed_entities),
            )
            return result

        cls._reconcile_workbench_reviews(conclusive_entity_ids, set())
        for entity_id, changed in changed_entities.items():
            entity = changed["entity"]
            changed_bindings = sorted(changed["binding_ids"])
            invalidated_template_count = cls.disable_entity(
                entity.id,
                binding_ids=changed_bindings,
                differences=changed["differences"],
                source_record_id=source_record_id,
            )
            if hasattr(entity, "refresh_from_db"):
                entity.refresh_from_db(fields=["status", "update_time"])
            cls._record_workbench_todo(
                entity,
                differences=changed["differences"],
                invalidated_template_count=invalidated_template_count,
            )
            result["changed_entity_count"] += 1
            result["invalidated_template_count"] += invalidated_template_count
            result["changed_entities"].append({
                "entity_id": entity.id,
                "entity_name": entity.name,
                "table_name": entity.table_name,
                "binding_ids": changed_bindings,
                "invalidated_template_count": invalidated_template_count,
                "differences": changed["differences"],
            })
        return result

    @classmethod
    def entity_signature(cls, entity_id: int) -> tuple:
        fields = DataFactoryField.objects.filter(entity_id=entity_id).order_by("sort", "id")
        return cls.columns_signature(fields.values(*cls.SIGNATURE_FIELDS))

    @classmethod
    def entity_signatures(cls, entity_ids: list[int]) -> dict[int, tuple]:
        grouped = {entity_id: [] for entity_id in entity_ids}
        fields = DataFactoryField.objects.filter(entity_id__in=entity_ids).order_by(
            "entity_id",
            "sort",
            "id",
        ).values("entity_id", *cls.SIGNATURE_FIELDS)
        for field in fields:
            grouped.setdefault(field["entity_id"], []).append(field)
        return {
            entity_id: cls.columns_signature(columns)
            for entity_id, columns in grouped.items()
        }

    @classmethod
    def columns_signature(cls, columns) -> tuple:
        return tuple(
            sorted(
                (
                    str(cls.column_value(column, "name") or ""),
                    cls.normalize_db_type(cls.column_value(column, "db_type")),
                    bool(cls.column_value(column, "nullable")),
                    bool(cls.column_value(column, "primary_key")),
                    bool(cls.column_value(column, "autoincrement")),
                    cls.normalize_max_length(
                        cls.column_value(column, "db_type"),
                        cls.column_value(column, "max_length"),
                    ),
                )
                for column in columns
            )
        )

    @staticmethod
    def normalize_db_type(db_type) -> str:
        value = re.sub(r"\s+", " ", str(db_type or "").strip().upper())
        value = re.sub(r"\s+COLLATE\s+[\"'`]?[^\s\"'`]+[\"'`]?", "", value)
        value = re.sub(r"\s+CHARACTER\s+SET\s+[^\s]+", "", value)
        value = re.sub(r"\s*([(),])\s*", r"\1", value)
        value = re.sub(
            r"\b(TINYINT|SMALLINT|MEDIUMINT|INT|INTEGER|BIGINT|FLOAT|DOUBLE|REAL|BIT|BOOL|BOOLEAN|DATETIME|TIMESTAMP|TIME|YEAR)"
            r"\s*\([^)]*\)",
            r"\1",
            value,
        )
        value = re.sub(r"\b(CHAR|VARCHAR|BINARY|VARBINARY)\s*\(\d+\)", r"\1", value)
        value = re.sub(r"\bINTEGER\b", "INT", value)
        value = re.sub(r"\s*(?:UNSIGNED|ZEROFILL)\b", "", value)
        if value.startswith("ENUM("):
            return "ENUM"
        if value.startswith("SET("):
            return "SET"
        return value

    @classmethod
    def normalize_max_length(cls, db_type, max_length):
        normalized_type = cls.normalize_db_type(db_type)
        if not any(item in normalized_type for item in ("CHAR", "BINARY")):
            return None
        try:
            return int(max_length) if max_length is not None else None
        except (TypeError, ValueError):
            return max_length

    @classmethod
    def should_block_auto_disable(cls, scanned_count: int, changed_count: int) -> bool:
        if changed_count > cls.BULK_DISABLE_MAX_COUNT:
            return True
        return (
                scanned_count >= cls.BULK_DISABLE_MIN_SCANNED_COUNT
                and changed_count / scanned_count > cls.BULK_DISABLE_MAX_RATIO
        )

    @staticmethod
    def describe_differences(expected: tuple, actual: tuple | None) -> list[dict]:
        expected_by_name = {item[0]: item[1:] for item in expected or ()}
        actual_by_name = {item[0]: item[1:] for item in actual or ()}
        differences = []
        for field_name in sorted(expected_by_name.keys() | actual_by_name.keys()):
            expected_value = expected_by_name.get(field_name)
            actual_value = actual_by_name.get(field_name)
            if expected_value == actual_value:
                continue
            if expected_value is None:
                change_type = "added"
            elif actual_value is None:
                change_type = "removed"
            else:
                change_type = "changed"
            differences.append({
                "field": field_name,
                "change_type": change_type,
                "expected": expected_value,
                "actual": actual_value,
            })
        return differences

    @classmethod
    def describe_incompatible_differences(
            cls,
            expected: tuple,
            actual: tuple | None,
            actual_columns: list[dict],
    ) -> list[dict]:
        expected_by_name = {item[0]: item[1:] for item in expected or ()}
        actual_by_name = {item[0]: item[1:] for item in actual or ()}
        actual_column_by_name = {
            str(column.get("name") or ""): column
            for column in actual_columns
        }
        differences = []
        for field_name in sorted(expected_by_name.keys() | actual_by_name.keys()):
            expected_value = expected_by_name.get(field_name)
            actual_value = actual_by_name.get(field_name)
            if expected_value is None:
                column = actual_column_by_name.get(field_name) or {}
                if (
                        not bool(column.get("nullable"))
                        and column.get("default") is None
                        and not bool(column.get("autoincrement"))
                        and not bool(column.get("generated"))
                ):
                    differences.append({
                        "field": field_name,
                        "change_type": "required_field_added",
                        "expected": None,
                        "actual": actual_value,
                    })
                else:
                    differences.append({
                        "field": field_name,
                        "change_type": "field_added",
                        "expected": None,
                        "actual": actual_value,
                    })
                continue
            if actual_value is None:
                differences.append({
                    "field": field_name,
                    "change_type": "configured_field_removed",
                    "expected": expected_value,
                    "actual": None,
                })
                continue

            reasons = []
            expected_type, expected_nullable, expected_primary, expected_auto, expected_length = expected_value
            actual_type, actual_nullable, actual_primary, actual_auto, actual_length = actual_value
            if DataFactoryDiscover.normalize_type(expected_type) != DataFactoryDiscover.normalize_type(actual_type):
                reasons.append("type_incompatible")
            if expected_nullable and not actual_nullable:
                reasons.append("nullable_became_required")
            if expected_primary != actual_primary:
                reasons.append("primary_key_changed")
            if expected_auto and not actual_auto:
                reasons.append("autoincrement_removed")
            if (
                    expected_length is not None
                    and actual_length is not None
                    and actual_length < expected_length
            ):
                reasons.append("max_length_reduced")
            if reasons:
                differences.append({
                    "field": field_name,
                    "change_type": "incompatible",
                    "reasons": reasons,
                    "expected": expected_value,
                    "actual": actual_value,
                })
            elif expected_value != actual_value:
                differences.append({
                    "field": field_name,
                    "change_type": "metadata_changed",
                    "expected": expected_value,
                    "actual": actual_value,
                })
        return differences

    @staticmethod
    def column_value(column, key: str):
        if isinstance(column, dict):
            return column.get(key)
        return getattr(column, key, None)

    @staticmethod
    def disable_entity(
            entity_id: int,
            binding_ids: list[int] | None = None,
            differences: list[dict] | None = None,
            source_record_id: int | None = None,
    ) -> int:
        differences = differences or []
        field_names = sorted({
            item.get("field")
            for database_diff in differences
            for item in database_diff.get("items") or []
            if item.get("field")
        })
        field_summary = "、".join(field_names[:5])
        if len(field_names) > 5:
            field_summary += f"等 {len(field_names)} 个字段"
        reason = "定时表结构巡检检测到数据库表结构已发生变化"
        if field_summary:
            reason += f"，涉及字段：{field_summary}"
        result = DataFactoryEntityService.change_status(
            entity_id=entity_id,
            status=StatusEnum.FAIL.value,
            source=DataFactoryEntityStatusChangeSourceEnum.SCHEMA_MONITOR.value,
            reason_code="schema_changed",
            reason=reason,
            source_record_type="schedule_fire",
            source_record_id=source_record_id,
            context={
                "job_key": "scan_data_factory_entity_field_updates",
                "binding_ids": sorted(binding_ids or []),
                "database_ids": sorted({
                    item.get("database_id")
                    for item in differences
                    if item.get("database_id") is not None
                }),
                "differences": differences,
            },
            invalidate_templates=True,
        )
        return result["invalidated_template_count"]
