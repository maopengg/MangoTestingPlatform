from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from typing import Any, TypeVar

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.forms import model_to_dict

ModelT = TypeVar("ModelT", bound=models.Model)


@dataclass(frozen=True)
class ModelMutationValidationError(Exception):
    errors: dict[str, Any]


def _validation_errors(error: ValidationError) -> dict[str, Any]:
    if hasattr(error, "message_dict"):
        return error.message_dict
    return {"non_field_errors": error.messages}


def _prepare_model(
        model: type[ModelT],
        payload: dict[str, Any],
        *,
        instance: ModelT | None = None,
        partial: bool = False,
) -> tuple[ModelT, dict[str, Any], list[str]]:
    target = instance or model()
    supplied_fields: set[str] = set()
    many_to_many: dict[str, Any] = {}
    unknown_fields: list[str] = []

    for name, value in payload.items():
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            unknown_fields.append(name)
            continue
        if not getattr(field, "editable", False) or field.auto_created:
            continue
        supplied_fields.add(field.name)
        if field.many_to_many:
            many_to_many[field.name] = value
        elif field.is_relation and field.many_to_one and not isinstance(value, models.Model):
            setattr(target, field.attname, value)
        else:
            setattr(target, field.name, value)

    if unknown_fields:
        raise ModelMutationValidationError(
            {name: ["未知字段"] for name in sorted(unknown_fields)}
        )

    excluded = []
    if partial:
        excluded = [
            field.name
            for field in model._meta.concrete_fields
            if field.name not in supplied_fields and field.primary_key is False
        ]
    return target, many_to_many, excluded


def validate_model(
        model: type[ModelT],
        payload: dict[str, Any],
        *,
        instance: ModelT | None = None,
        partial: bool = False,
) -> None:
    candidate = copy(instance) if instance is not None else None
    target, _, excluded = _prepare_model(
        model,
        payload,
        instance=candidate,
        partial=partial,
    )
    try:
        target.full_clean(exclude=excluded)
    except ValidationError as error:
        raise ModelMutationValidationError(_validation_errors(error)) from error


def save_model(
        model: type[ModelT],
        payload: dict[str, Any],
        *,
        instance: ModelT | None = None,
        partial: bool = False,
) -> ModelT:
    """Persist a model without coupling the domain layer to DRF."""

    target, many_to_many, excluded = _prepare_model(
        model,
        payload,
        instance=instance,
        partial=partial,
    )
    try:
        target.full_clean(exclude=excluded)
    except ValidationError as error:
        raise ModelMutationValidationError(_validation_errors(error)) from error
    target.save()
    for name, value in many_to_many.items():
        getattr(target, name).set(value or [])
    return target


def model_payload(instance: models.Model) -> dict[str, Any]:
    payload = model_to_dict(instance)
    payload[instance._meta.pk.name] = instance.pk
    return payload
