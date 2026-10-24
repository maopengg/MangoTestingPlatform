from __future__ import annotations

from typing import Any

from django.db.models import Q


def normalize_test_envs(value: Any, fallback: Any = None) -> list[int]:
    if value in [None, "", "null", "undefined"]:
        value = fallback
    if value in [None, "", "null", "undefined"]:
        return []
    if not isinstance(value, (list, tuple, set)):
        value = [value]
    result = []
    for item in value:
        if item in [None, "", "null", "undefined"]:
            continue
        try:
            env = int(item)
        except (TypeError, ValueError):
            continue
        if env not in result:
            result.append(env)
    return result


def test_envs_query(test_env: Any, field_name: str = "test_envs") -> Q:
    query = Q(**{field_name: []}) | Q(**{f"{field_name}__isnull": True})
    envs = normalize_test_envs(test_env)
    if envs:
        query |= Q(**{f"{field_name}__contains": [envs[0]]})
    return query


def test_envs_filter_query(value: Any, field_name: str = "test_envs") -> Q:
    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    values = []
    for item in raw_values:
        values.extend(str(item).split(','))

    query = Q(pk__in=[])
    if "__common__" in values:
        query |= Q(**{field_name: []}) | Q(**{f"{field_name}__isnull": True})
    for env in normalize_test_envs(values):
        query |= Q(**{f"{field_name}__contains": [env]})
    return query


def test_envs_titles(test_envs: list[int], enum_cls) -> list[str]:
    return [enum_cls.get_value(item) or str(item) for item in normalize_test_envs(test_envs)]


def sync_test_env_attrs(attrs: dict, instance=None):
    if "test_envs" in attrs:
        test_envs = normalize_test_envs(attrs.get("test_envs"))
    elif "test_env" in attrs:
        test_envs = normalize_test_envs(attrs.get("test_env"))
    elif instance is not None and getattr(instance, "test_envs", None):
        test_envs = normalize_test_envs(getattr(instance, "test_envs", None))
    elif instance is not None:
        test_envs = normalize_test_envs(getattr(instance, "test_env", None))
    else:
        test_envs = []
    attrs["test_envs"] = test_envs
    attrs["test_env"] = test_envs[0] if test_envs else None
    return attrs
