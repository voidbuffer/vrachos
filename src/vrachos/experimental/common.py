"""Experimental common and internal."""

import json
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel


def get_utc_timestamp() -> str:
    """Generate UTC timestamp string for log filenames (safe for all OS)."""
    return datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")


def is_user_defined_instance(obj: Any) -> bool:
    """Check if object is a user-defined instance, not a builtin type."""
    return not isinstance(obj, type) and type(obj).__module__ != "builtins"


def is_unified_diff(text: Any) -> bool:
    """Check if string looks like a unified diff format."""
    if not isinstance(text, str):
        return False
    lines = text.splitlines()
    if len(lines) < 3:
        return False
    # check first two lines for --- and +++
    if not (lines[0].startswith("--- ") and lines[1].startswith("+++ ")):
        return False
    # check for at least one hunk header
    return any(line.startswith("@@ ") for line in lines[2:])


def get_model_schema(model: type[BaseModel]) -> str:
    """Get BaseModel schema as formatted JSON string without validation."""
    schema = model.model_json_schema()
    return json.dumps(schema, indent=4)


def get_model_json(instance: BaseModel) -> str:
    """Get JSON string representation of a BaseModel instance."""
    return instance.model_dump_json(indent=4)


def get_model_defaults_json(model: type[BaseModel]) -> str:
    """Get model defaults as JSON string."""
    defaults: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        if field_info.is_required():
            defaults[field_name] = None
        elif field_info.default_factory is not None:
            try:
                # Call the factory with no arguments
                defaults[field_name] = field_info.default_factory()  # type: ignore[call-arg]
            except TypeError:
                defaults[field_name] = None
        else:
            defaults[field_name] = field_info.default
    return json.dumps(defaults, indent=4, default=str)
