"""Compile only explicitly target-visible data; grading truth never enters the source."""

from copy import deepcopy


def compile_target_input(dataset_item, input_variable="case_input", input_variables=None):
    from src.apps.evaluation.formatters.payload import apply_mapping
    variables = input_variables or getattr(dataset_item, "input_variables", None)
    result = {item["name"]: apply_mapping(dataset_item.input_data, {"paths": [item["path"]]}) for item in variables} if variables else {input_variable: deepcopy(dataset_item.input_data)}
    runtime = getattr(dataset_item, "runtime_context", None) or {}
    return {**deepcopy(runtime), **result}
