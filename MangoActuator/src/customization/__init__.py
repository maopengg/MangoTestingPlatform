# -*- coding: utf-8 -*-
from copy import deepcopy

from mangotools.decorator import func_info as assertion_func_info

from src.customization.assertion import ObtainAssertion
from src.customization.database import ObtainDatabase, database_driver_info
from src.customization.test_data import ObtainTestData
from src.customization.ui_steps import func_info as ui_step_func_info


def _merge_method_trees(*trees: list[dict]) -> list[dict]:
    merged: list[dict] = []
    index: dict[str, dict] = {}
    for tree in trees:
        for item in tree:
            if not item:
                continue
            value = item.get('value')
            if value not in index:
                copied = deepcopy(item)
                copied['children'] = list(copied.get('children') or [])
                merged.append(copied)
                index[value] = copied
                continue
            existing = index[value]
            known_children = {child.get('value') for child in existing.get('children') or []}
            for child in item.get('children') or []:
                if child.get('value') not in known_children:
                    existing.setdefault('children', []).append(deepcopy(child))
                    known_children.add(child.get('value'))
    return merged


func_info = _merge_method_trees(ui_step_func_info, assertion_func_info)

__all__ = [
    'ObtainAssertion',
    'ObtainDatabase',
    'ObtainTestData',
    'assertion_func_info',
    'database_driver_info',
    'func_info',
    'ui_step_func_info',
]
