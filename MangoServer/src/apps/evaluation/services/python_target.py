"""Run user-authored targets outside the Django process with bounded output/time."""

import ast
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory

from src.apps.evaluation.exceptions import EVALUATION_TARGET_CALL_FAILED, EvaluationError
from src.apps.evaluation.services.validation import invalid_config


def compile_python_target(code, variables=None):
    prefix = "__mango_eval_slot_"
    while prefix in code:
        prefix += "_"
    bindings = {}
    def marker(match):
        name = f"{prefix}{len(bindings)}__"
        bindings[name] = match.group(1).strip()
        return name
    source = re.sub(r"\$\{\{(.*?)\}\}", marker, code)
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise invalid_config(f"Python 脚本第 {error.lineno} 行语法错误") from error
    if not any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in tree.body):
        raise invalid_config("Python 脚本必须定义 main(input, context) 函数")
    pattern = re.compile("(" + "|".join(re.escape(key) for key in bindings) + ")") if bindings else None
    class ReplaceVariables(ast.NodeTransformer):
        def value(self, marker_name):
            name = bindings[marker_name]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) or (variables is not None and name not in variables):
                raise invalid_config("Python 中的替换变量必须与评测数据配置的输入变量名一致")
            return ast.Subscript(value=ast.Name(id="__mango_evaluation_inputs__", ctx=ast.Load()), slice=ast.Constant(name), ctx=ast.Load())
        def visit_Name(self, node):
            if node.id in bindings:
                if not isinstance(node.ctx, ast.Load):
                    raise invalid_config("替换变量只能用于读取数据")
                return ast.copy_location(self.value(node.id), node)
            return node
        def parts(self, text):
            return [ast.FormattedValue(value=self.value(part), conversion=-1) if part in bindings else ast.Constant(part)
                    for part in pattern.split(text) if part]
        def visit_Constant(self, node):
            if isinstance(node.value, str) and pattern and pattern.search(node.value):
                replacement = self.value(node.value) if node.value in bindings else ast.JoinedStr(values=self.parts(node.value))
                return ast.copy_location(replacement, node)
            return node
        def visit_JoinedStr(self, node):
            values = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str) and pattern and pattern.search(value.value):
                    values.extend(self.parts(value.value))
                else:
                    values.append(self.visit(value))
            node.values = values
            return node
    return ast.unparse(ast.fix_missing_locations(ReplaceVariables().visit(tree)))


def validate_python_target(code):
    compile_python_target(code)


def run_python_target(code, input_data, context, timeout):
    code = compile_python_target(code, variables=input_data)
    runner = Path(__file__).resolve().parents[3] / "processes" / "evaluation_script" / "runner.py"
    with TemporaryDirectory(prefix="evaluation-script-") as directory:
        root = Path(directory)
        (root / "target.py").write_text(code, encoding="utf-8")
        (root / "input.json").write_text(json.dumps({"input": input_data, "context": context}, ensure_ascii=False), encoding="utf-8")
        process = subprocess.Popen(
            [sys.executable, "-I", str(runner)], cwd=root,
            env={key: os.environ[key] for key in ("PATH", "SYSTEMROOT") if key in os.environ},
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise EvaluationError(EVALUATION_TARGET_CALL_FAILED, value=("Python 脚本执行超时",)) from error
        finally:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            process.wait()
        result_file = root / "output.json"
        if process.returncode or not result_file.exists() or result_file.stat().st_size > 2 * 1024 * 1024:
            raise EvaluationError(EVALUATION_TARGET_CALL_FAILED, value=("Python 脚本失败，请检查函数及 JSON 返回值",))
        try:
            output = json.loads(result_file.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as error:
            raise EvaluationError(EVALUATION_TARGET_CALL_FAILED, value=("Python 脚本必须返回 JSON 对象",)) from error
        if not isinstance(output, dict):
            raise EvaluationError(EVALUATION_TARGET_CALL_FAILED, value=("Python 脚本必须返回 JSON 对象",))
        return output
