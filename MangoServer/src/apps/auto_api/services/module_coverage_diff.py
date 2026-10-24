"""模块覆盖率快照差异计算。"""


def build_structured_diff(current, previous, ignored_fields: set[str] | None = None):
    ignored = ignored_fields or {
        "id",
        "create_time",
        "scan",
        "coverage_case",
        "interface_snapshot",
        "submitted_hash",
        "sync_action",
    }

    def flatten(value, prefix=""):
        if not isinstance(value, dict):
            return {prefix: value}
        result = {}
        for key in sorted(value):
            field = f"{prefix}.{key}" if prefix else key
            if not prefix and key in ignored:
                continue
            nested = value[key]
            if isinstance(nested, dict):
                result.update(flatten(nested, field))
            else:
                result[field] = nested
        return result

    current_fields = flatten(current or {})
    previous_fields = flatten(previous or {})
    changed_fields = sorted(
        field
        for field in set(current_fields) | set(previous_fields)
        if current_fields.get(field) != previous_fields.get(field)
    )
    return {
        "changed": bool(changed_fields),
        "changed_fields": changed_fields,
        "changes": [
            {
                "field": field,
                "previous": previous_fields.get(field),
                "current": current_fields.get(field),
            }
            for field in changed_fields
        ],
    }
