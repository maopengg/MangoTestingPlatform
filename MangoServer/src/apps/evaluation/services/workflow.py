"""Dataset-owned preparation and reference execution with bounded polling and cleanup."""

from copy import deepcopy
from contextlib import contextmanager
import json
import re
import time
import uuid
from types import SimpleNamespace
from src.apps.evaluation.enums.workflow import (
    EvaluationWorkflowActionEnum as Action, EvaluationWorkflowStageEnum as Stage,
    EvaluationWorkflowScopeEnum as Scope,
)
from src.apps.evaluation.formatters.payload import apply_mapping, mask_sensitive, select_value, canonical_json
from src.apps.evaluation.services.target_input import compile_target_input
from src.apps.evaluation.services.validation import invalid_config
from src.apps.evaluation.services.failure import failure_message
from src.apps.evaluation.exceptions import EvaluationError


def replace_workflow_values(value, variables, _depth=0):
    if _depth > 20:
        raise invalid_config("流程变量存在循环引用或引用层数过深")
    if isinstance(value, dict):
        return {key: replace_workflow_values(item, variables, _depth) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_workflow_values(item, variables, _depth) for item in value]
    if not isinstance(value, str):
        return value
    pattern = r"\$\{\{\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\}\}"
    missing = object()
    def read(name):
        result = select_value(variables, name, missing)
        if result is missing:
            raise invalid_config(f"流程引用尚未产生或不存在：{name}")
        return replace_workflow_values(deepcopy(result), variables, _depth + 1)
    match = re.fullmatch(pattern, value)
    if match:
        return read(match.group(1))
    return re.sub(pattern, lambda match: str(read(match.group(1))), value)


class EvaluationWorkflowRunner:
    def __init__(self, execution, config):
        self.execution, self.config = execution, config
        self.workflow = config.dataset_config.workflow
        self.bindings = {binding.resource: binding for binding in self.workflow.bindings}
        self.execution_state = self.new_state()
        self.groups = {}
        self.current = None
        self.records = []
        self.cleanup_errors = []
        self.failed_groups = {}

    def new_state(self):
        return {"steps": {}, "session": {"id": uuid.uuid4().hex}, "execution": {"id": self.execution.id}, "factories": []}

    def stopped(self):
        from src.apps.evaluation.models import EvaluationCaseExecution
        return EvaluationCaseExecution.objects.filter(id=self.execution.id, stop_requested=True).exists()

    def persist(self):
        self.execution.details = {**(self.execution.details or {}), "workflow": mask_sensitive(self.records), "cleanup_errors": self.cleanup_errors}
        self.execution.save(update_fields=["details", "update_time"])

    def run_stage(self, stage, scope, state, sample=None, row=None):
        for step in self.workflow.steps:
            if step.stage != stage or step.scope != scope:
                continue
            if step.turn_kind and step.turn_kind.value != state.get("turn", {}).get("kind"):
                continue
            if stage != Stage.CLEANUP and self.stopped():
                raise invalid_config("执行已停止")
            record = {"step_id": step.id, "name": step.name, "stage": stage.value, "scope": scope.value,
                      "item_id": getattr(row, "dataset_item_id", None), "status": "running", "output": None}
            self.records.append(record)
            self.persist()
            started = time.monotonic()
            try:
                variables = {key: value for key, value in state.items() if key != "factories"}
                if sample is not None:
                    for item in self.config.dataset_config.input_variables:
                        try:
                            variables.update(compile_target_input(SimpleNamespace(input_data=sample.input_data), input_variables=[item.model_dump()]))
                        except EvaluationError:
                            continue
                arguments = replace_workflow_values(step.input_data, variables)
                if step.iterate_path:
                    entries = apply_mapping(arguments, {"paths": [step.iterate_path]})
                    if not isinstance(entries, list) or len(entries) > 1000:
                        raise invalid_config("列表循环需要不超过 1000 个元素的数组")
                    output = []
                    state["steps"][step.id] = output
                    output_bytes = 0
                    for entry in entries:
                        item_arguments = {**arguments, "item": entry} if isinstance(arguments, dict) else {"item": entry}
                        result = self.call_until(step, item_arguments, state, started)
                        output_bytes += len(canonical_json(result).encode())
                        if output_bytes > 2_000_000:
                            raise invalid_config("流程列表累计输出超过 2 MB")
                        output.append(result)
                        record["output"] = mask_sensitive(deepcopy(output))
                        self.persist()
                else:
                    output = self.call_until(step, arguments, state, started)
                if stage != Stage.REFERENCE:
                    state["steps"][step.id] = output
                record.update(status="success", output=mask_sensitive(output))
                if stage == Stage.REFERENCE and sample is not None:
                    wrapped = isinstance(output, dict) and "expected_output" in output
                    expected = output["expected_output"] if wrapped else output
                    sample.expected_output = deepcopy(expected if isinstance(expected, dict) else {"value": expected})
                    if wrapped and "input_data" in output:
                        sample.input_data = deepcopy(output["input_data"])
                    if wrapped and "context" in output:
                        if not isinstance(output["context"], dict):
                            raise invalid_config("标准答案 context 必须为对象")
                        sample.context = deepcopy(output["context"])
            except Exception as error:
                record.update(status="failed", error_message=failure_message(error))
                if stage != Stage.CLEANUP:
                    raise
                self.cleanup_errors.append(f"{step.name}：{failure_message(error)}")
            finally:
                record["duration_ms"] = round((time.monotonic() - started) * 1000)
                self.persist()

    def call_until(self, step, arguments, state, started):
        while True:
            if step.stage != Stage.CLEANUP and self.stopped():
                raise invalid_config("执行已停止")
            elapsed = time.monotonic() - started
            if elapsed >= step.timeout_seconds:
                raise invalid_config("流程步骤执行或等待超时")
            output = self.call(step, arguments, state, max(1, step.timeout_seconds - int(elapsed)))
            output = json.loads(canonical_json(apply_mapping(output, {"paths": step.paths})))
            if len(json.dumps(output, default=str).encode()) > 2_000_000:
                raise invalid_config("流程步骤输出超过 2 MB")
            if step.failure_path and self.matches(output, step.failure_path, step.failure_value):
                raise invalid_config("异步任务返回失败状态")
            if not step.until_path or self.matches(output, step.until_path, step.until_value):
                return output
            remaining = min(step.interval_seconds, max(0, step.timeout_seconds - (time.monotonic() - started)))
            while remaining > 0:
                if step.stage != Stage.CLEANUP and self.stopped():
                    raise invalid_config("执行已停止")
                delay = min(0.25, remaining)
                time.sleep(delay)
                remaining -= delay

    @staticmethod
    def matches(output, path, expected):
        try:
            value = apply_mapping(output, {"paths": [path]})
            return type(value) is type(expected) and value == expected
        except EvaluationError:
            return False

    def call(self, step, arguments, state, timeout):
        from src.apps.evaluation.services.python_target import run_python_target
        from src.apps.evaluation.selectors.workflow import require_resource_access
        if step.action == Action.SCRIPT:
            return run_python_target(step.code, arguments if isinstance(arguments, dict) else {"case_input": arguments},
                                     {key: value for key, value in state.items() if key != "factories"}, timeout)
        binding = self.bindings[step.resource]
        require_resource_access(step.action, self.execution.created_by, binding.project_product_id)
        from src.apps.test_center.enums.environment import EnvironmentEnum
        if step.action in {Action.SQL, Action.FACTORY} and self.execution.test_env == EnvironmentEnum.PRO.value:
            raise invalid_config("生产环境不允许测评流程执行 SQL 或数据工厂")
        if step.action == Action.API:
            from src.apps.auto_api.services.test_case.test_api_info import TestApiInfo
            from src.apps.evaluation.services.adapters import BaseTargetAdapter
            runtime = TestApiInfo(user_id=self.execution.created_by_id, test_env=self.execution.test_env)
            runtime.test_setup.timeout = timeout
            parameters = arguments if isinstance(arguments, dict) else {"case_input": arguments}
            output = runtime.api_info_run(binding.ref_id, revision_id=binding.revision_id, runtime_parameters=parameters)
            BaseTargetAdapter.ensure_response_available(output, failed=output.get("call_success") is False)
            return output
        if step.action == Action.SQL:
            from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService
            if not DataSourceExecutionService.is_sql_query(step.code):
                raise invalid_config("流程 SQL 只允许查询；创建测试数据请使用接口或数据工厂")
            return DataSourceExecutionService.execute(datasource_alias_id=binding.ref_id,
                project_product_id=binding.project_product_id, test_env=self.execution.test_env,
                operation_config=step.code, parameters=arguments,
                source_context={"source_type": "evaluation", "source_stage": step.stage.value, "source_id": self.execution.id})
        from src.apps.data_factory.enums import DataFactoryExecutionSourceEnum
        from src.apps.data_factory.services.runner import DataFactoryRunner
        result = DataFactoryRunner.run_template(template_id=binding.ref_id,
            source_type=DataFactoryExecutionSourceEnum.SYSTEM.value, source_id=self.execution.id,
            overrides=arguments, context={"__executor": {"user_id": self.execution.created_by_id}}, test_env=self.execution.test_env)
        state["factories"].append(result["execution_id"])
        return result

    def cleanup(self, scope, state, sample=None, row=None):
        self.run_stage(Stage.CLEANUP, scope, state, sample, row)
        from src.apps.data_factory.services.cleanup import DataFactoryCleanup
        for execution_id in reversed(state["factories"]):
            try:
                result = DataFactoryCleanup.cleanup_execution(execution_id, force_cleanup=True, allow_missing=True)
                if result.get("fail"):
                    raise invalid_config("工厂创建的数据未全部清理")
            except Exception as error:
                self.cleanup_errors.append(f"数据工厂 {execution_id}：{failure_message(error)}")
        self.persist()

    @contextmanager
    def execution_scope(self):
        try:
            for stage in (Stage.PREPARE, Stage.READY):
                self.run_stage(stage, Scope.EXECUTION, self.execution_state)
            yield self
        finally:
            for state, sample, row in reversed(list(self.groups.values())):
                self.cleanup(Scope.GROUP, state, sample, row)
            self.cleanup(Scope.EXECUTION, self.execution_state)

    @contextmanager
    def item_scope(self, row, sample):
        scenario = row.item_snapshot.get("scenario") or {}
        group_key = (scenario.get("group_key") or row.dataset_item_id, row.repeat_index)
        if group_key in self.failed_groups:
            raise invalid_config(self.failed_groups[group_key])
        if group_key not in self.groups:
            state = deepcopy(self.execution_state)
            state["factories"] = []
            state["session"] = {"id": uuid.uuid4().hex}
            self.groups[group_key] = (state, sample, row)
            try:
                for stage in (Stage.PREPARE, Stage.READY):
                    self.run_stage(stage, Scope.GROUP, state, sample, row)
            except Exception as error:
                self.failed_groups[group_key] = failure_message(error)
                raise
        parent = self.groups[group_key][0]
        state = deepcopy(parent)
        state["factories"] = []
        try:
            for stage in (Stage.PREPARE, Stage.READY):
                self.run_stage(stage, Scope.ITEM, state, sample, row)
            yield state
        finally:
            self.cleanup(Scope.ITEM, state, sample, row)
            parent["steps"].update(state["steps"])
