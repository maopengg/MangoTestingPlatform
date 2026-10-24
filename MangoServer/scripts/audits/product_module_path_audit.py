#!/usr/bin/env python3
import ast
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = SERVER_ROOT / 'src'
MODULE_SERIALIZERS = {'ProductModuleSerializers', 'ProductModuleSerializersC'}


def call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def nested_module_fields(class_node):
    fields = []
    for node in class_node.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or call_name(value.func) not in MODULE_SERIALIZERS:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        fields.extend(target.id for target in targets if isinstance(target, ast.Name))
    return fields


def eager_loaded_module_fields(class_node):
    loaded_fields = set()
    for node in class_node.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != 'setup_eager_loading':
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or call_name(child.func) != 'with_full_paths':
                continue
            loaded_fields.update(
                argument.value
                for argument in child.args[1:]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            )
    return loaded_fields


def main():
    issues = []
    checked = 0
    for path in sorted(SOURCE_ROOT.rglob('*.py')):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as error:
            issues.append(f'{path.relative_to(SERVER_ROOT)}: 无法解析：{error}')
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            module_fields = nested_module_fields(node)
            if not module_fields:
                continue
            checked += 1
            loaded_fields = eager_loaded_module_fields(node)
            missing_fields = sorted(set(module_fields) - loaded_fields)
            if missing_fields:
                issues.append(
                    f'{path.relative_to(SERVER_ROOT)}:{node.lineno} {node.name} '
                    f'缺少 ProductModuleService.with_full_paths(queryset, '
                    f'{", ".join(repr(field) for field in missing_fields)})'
                )

    print('Product module path audit')
    print(f'Checked serializers: {checked}')
    if issues:
        print(f'Issues: {len(issues)}')
        for issue in issues:
            print(f'- {issue}')
        raise SystemExit(1)
    print('Issues: 0')


if __name__ == '__main__':
    main()
