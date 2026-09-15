"""Enum helpers shared by the ORM models."""

import enum
from typing import Any


def enum_values(enum_class: type[enum.Enum]) -> list[str]:
    """Store the `.value` of a Python enum instead of its member name.

    Without this SQLAlchemy persists ``COMPLIANT`` while the API and the
    frontend speak ``compliant``, which makes raw SQL filtering confusing.
    """
    return [member.value for member in enum_class]


def coerce_enum(enum_class: type[enum.Enum], value: Any) -> enum.Enum | None:
    """Best-effort conversion of a loosely typed value into an enum member."""
    if value is None or isinstance(value, enum_class):
        return value
    try:
        return enum_class(str(value).lower())
    except ValueError:
        return None
