from __future__ import annotations

from django.db import models
from django.utils import timezone

from src.interfaces.mcp.common import current_user


def mcp_current_user_id() -> int:
    return current_user().id


def model_has_field(model, field_name: str) -> bool:
    if model is None:
        return False
    try:
        model._meta.get_field(field_name)
    except Exception:
        return False
    return True


def mcp_with_update_user(payload: dict | None, field_name: str = "update_user") -> dict:
    data = dict(payload or {})
    data[field_name] = mcp_current_user_id()
    return data


def mcp_inside_post(crud_cls, payload: dict | None, field_name: str = "update_user") -> dict:
    data = dict(payload or {})
    if model_has_field(getattr(crud_cls, "model", None), field_name):
        data[field_name] = mcp_current_user_id()
    return crud_cls.inside_post(data)


def mcp_inside_put(crud_cls, instance_id: int, payload: dict | None, field_name: str = "update_user") -> dict:
    data = dict(payload or {})
    data.setdefault("id", instance_id)
    if model_has_field(getattr(crud_cls, "model", None), field_name):
        data[field_name] = mcp_current_user_id()
    return crud_cls.inside_put(instance_id, data)


def mcp_set_update_user(instance: models.Model, field_name: str = "update_user") -> bool:
    attr_name = f"{field_name}_id"
    if not hasattr(instance, attr_name):
        return False
    setattr(instance, attr_name, mcp_current_user_id())
    return True


def mcp_save_update_user(
        instance: models.Model,
        update_fields: list[str] | tuple[str, ...] | None = None,
        field_name: str = "update_user",
):
    fields = list(update_fields) if update_fields is not None else None
    if mcp_set_update_user(instance, field_name) and fields is not None and field_name not in fields:
        fields.append(field_name)
    if hasattr(instance, "update_time"):
        instance.update_time = timezone.now()
        if fields is not None and "update_time" not in fields:
            fields.append("update_time")
    instance.save(update_fields=fields)


def mcp_update_kwargs(model, values: dict | None = None, field_name: str = "update_user") -> dict:
    data = dict(values or {})
    if model_has_field(model, field_name):
        data[f"{field_name}_id"] = mcp_current_user_id()
    if model_has_field(model, "update_time"):
        data["update_time"] = timezone.now()
    return data
