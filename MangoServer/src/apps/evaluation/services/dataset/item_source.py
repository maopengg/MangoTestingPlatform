"""Freeze and resolve each dataset item's independent data source."""

from copy import deepcopy
import time
from pydantic import ValidationError
from src.apps.evaluation.enums.data_source import EvaluationItemSourceEnum as Kind
from src.apps.evaluation.enums.workflow import EvaluationWorkflowActionEnum as Action
from src.apps.evaluation.enums.workflow import EvaluationWorkflowStageEnum as Stage
from src.apps.evaluation.schemas.data_source import EvaluationItemDataSource
from src.apps.evaluation.schemas.workflow import EvaluationWorkflowStep
from src.apps.evaluation.formatters.payload import content_hash, mask_sensitive, plaintext_secret_paths, apply_mapping
from src.apps.evaluation.selectors.workflow import resource_configuration
from src.apps.evaluation.services.assets.validation import invalid_config
from src.apps.evaluation.services.execution.failure import failure_message


def validate_item_source(value):
    try:
        source = EvaluationItemDataSource.model_validate(value or {})
    except ValidationError as error:
        raise invalid_config(str(error)) from error
    if plaintext_secret_paths(source.model_dump(mode="json")):
        raise invalid_config("条目数据来源中的敏感信息必须使用凭据引用")
    if source.kind == Kind.SQL:
        from src.apps.data_factory.services.datasource.data_source_execution import DataSourceExecutionService
        from src.apps.data_factory.exceptions import DataFactoryError
        try:
            is_query = DataSourceExecutionService.is_sql_query(source.query)
        except DataFactoryError as error:
            raise invalid_config("条目 SQL 必须是一条只读查询") from error
        if not is_query:
            raise invalid_config("条目 SQL 只允许查询；创建数据请使用数据工厂")
    return source


def freeze_item_source(value, user, *, product_id=None):
    source = validate_item_source(value)
    if source.kind == Kind.MANUAL:
        return {}
    if product_id is not None and source.binding.project_product_id != product_id:
        raise invalid_config("条目数据来源不属于当前 Case 的项目产品")
    action = Action(source.kind.value)
    revision, configuration = resource_configuration(action, source.binding, user)
    if source.kind == Kind.FACTORY:
        from src.apps.data_factory.selectors.template import template_configuration
        configuration = template_configuration(source.binding.ref_id, source.binding.project_product_id, overrides=source.parameters)
        if configuration is None:
            raise invalid_config("条目数据工厂参数引用的模板不可用")
    if source.kind == Kind.SQL:
        from src.apps.test_center.enums.data_source import DataSourceTypeEnum
        if configuration.get("db_type") not in {DataSourceTypeEnum.MYSQL.value, DataSourceTypeEnum.POSTGRESQL.value, DataSourceTypeEnum.SQLITE.value}:
            raise invalid_config("条目 SQL 来源只支持关系型数据库")
    digest = content_hash(configuration)
    if source.binding.content_hash and source.binding.content_hash != digest:
        raise invalid_config("条目数据来源已变更，请复制测评集草稿并重新绑定")
    source.binding.content_hash = digest
    source.binding.revision_id = revision
    return source.model_dump(mode="json")


def resolve_item_source(runner, row, sample, state):
    from src.apps.evaluation.services.workflow.workflow import replace_workflow_values
    from src.apps.evaluation.services.targets.target_input import compile_target_input
    source = validate_item_source(row.item_snapshot.get("data_source"))
    if source.kind == Kind.MANUAL:
        return {}
    freeze_item_source(source.model_dump(mode="json"), runner.execution.created_by,
                       product_id=runner.execution.case.project_product_id)
    action = Action(source.kind.value)
    step = EvaluationWorkflowStep(id="item_source", name="条目数据来源", stage=Stage.PREPARE,
        action=action, resource="item_source", code=source.query, timeout_seconds=source.timeout_seconds)
    source_state = {"steps": {}, "session": deepcopy(state["session"]), "execution": deepcopy(state["execution"]), "factories": state["factories"]}
    arguments = replace_workflow_values(source.parameters, {**compile_target_input(sample),
        "session": source_state["session"], "execution": source_state["execution"]})
    record = {"step_id": "item_source", "name": "条目数据来源", "stage": "prepare", "scope": "item", "item_id": row.dataset_item_id,
              "status": "running", "output": None}
    runner.records.append(record)
    runner.persist()
    started = time.monotonic()
    previous = runner.bindings.get("item_source")
    runner.bindings["item_source"] = source.binding
    try:
        result = runner.call_until(step, arguments, source_state, started)
        if source.kind == Kind.SQL:
            rows = result.get("rows", [])
            if not rows:
                raise invalid_config("条目 SQL 未查询到数据，未调用被测目标")
            if result.get("truncated"):
                raise invalid_config("条目 SQL 结果被截断，请缩小查询范围")
            values = {}
            if source.key:
                from mangotools.data_processor import CacheTool
                cache = CacheTool()
                cache.set_sql_cache(source.key, rows[0])
                values.update(cache.get_all())
        elif source.kind == Kind.API:
            values = {variable.name: apply_mapping(result, {"paths": [variable.path]}) for variable in source.variables}
        else:
            values = {"data": result.get("output", result.get("data", {}))}
        record.update(status="success", output=mask_sensitive(result))
        return values
    except Exception as error:
        record.update(status="failed", error_message=failure_message(error))
        raise
    finally:
        if previous is None:
            runner.bindings.pop("item_source", None)
        else:
            runner.bindings["item_source"] = previous
        record["duration_ms"] = round((time.monotonic() - started) * 1000)
        runner.persist()
