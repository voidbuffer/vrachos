"""Operation utilities for Pydantic models."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from difflib import unified_diff
from typing import Any, cast, get_type_hints

from pydantic import BaseModel, Field, create_model, field_validator
from rich.console import Console
from rich.syntax import Syntax


def make_partial[T: BaseModel](model: type[T]) -> type[T]:
    """Create a partial Pydantic model where all fields are optional."""
    hints = get_type_hints(model)
    field_defs: dict[str, tuple[Any, Any]] = {}

    for name, typ in hints.items():
        field_defs[name] = (typ | None, None)

    Partial = create_model(
        f"Partial{model.__name__}",
        **cast(dict[str, Any], field_defs),
    )
    return Partial  # type: ignore[no-any-return]


class ModelOps[T: BaseModel]:
    """Operations on pydantic models."""

    def __init__(self, obj: T) -> None:
        """Initialize ModelOps with a Pydantic model instance."""
        self.obj: T = obj

    def __str__(self) -> str:
        """Return formatted JSON string representation."""
        console = Console(record=True)
        with console.capture() as capture:
            console.print(
                Syntax(
                    self.obj.model_dump_json(indent=4),
                    "json",
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=False,
                )
            )
        return capture.get()

    def __repr__(self) -> str:
        """Return formatted JSON string representation."""
        return self.__str__()

    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return self.obj.model_dump()

    def to_json(self) -> str:
        """Convert model to JSON string representation."""
        return self.obj.model_dump_json(indent=4)

    def fields(self) -> list[str]:
        """Get list of all model field names."""
        return list(self.obj.__class__.model_fields.keys())

    def schema(self) -> dict[str, Any]:
        """Get the Pydantic JSON schema for introspection."""
        return self.obj.__class__.model_json_schema()

    def update(self, **kwargs: Any) -> T:
        """Create a new instance with updated fields."""
        data = self.to_dict()
        data.update(kwargs)
        return self.obj.__class__(**data)

    def diff(self, other: T) -> dict[str, tuple[Any, Any]]:
        """Return fields that differ: {field: (old, new)}."""
        o1 = self.to_dict()
        o2 = ModelOps(other).to_dict()

        out = {}
        for k in set(o1) | set(o2):
            if o1.get(k) != o2.get(k):
                out[k] = (o1.get(k), o2.get(k))
        return out

    def model_diff(self, b: T) -> BaseModel:
        """Return a partial model with only differing fields."""
        if type(self.obj) is not type(b):
            raise TypeError("Models must be the same type")

        Partial = make_partial(type(self.obj))
        diff_data = {}

        for field in self.obj.__class__.model_fields:
            av = getattr(self.obj, field)
            bv = getattr(b, field)
            if av != bv:
                diff_data[field] = bv

        return Partial(**diff_data)

    def udiff(self, b: BaseModel) -> str:
        """Return unified diff between two models."""
        a_json = self.obj.model_dump_json(indent=4).splitlines(keepends=True)
        b_json = b.model_dump_json(indent=4).splitlines(keepends=True)
        diff_lines = list(
            unified_diff(a_json, b_json, fromfile="a", tofile="b")
        )
        return "".join(diff_lines)

    def merge(self, other: T) -> T:
        """Shallow merge with another instance."""
        d1 = self.to_dict()
        d2 = ModelOps(other).to_dict()
        merged = {**d1, **d2}
        return self.obj.__class__(**merged)

    @staticmethod
    def model_to_json(obj: BaseModel) -> str:
        """Serialize model to formatted JSON string."""
        return json.dumps(obj.model_dump(), indent=4, sort_keys=True)


if __name__ == "__main__":
    from ui import UI

    class User(BaseModel):
        """User model."""

        id: int = Field(..., ge=1)
        username: str = Field(..., min_length=3, max_length=32)
        email: str
        tags: list[str] = Field(default_factory=list)
        created_at: datetime = Field(
            default_factory=lambda: datetime.now(tz=UTC)
        )

        @field_validator("username")
        @classmethod
        def no_space_in_usernames(cls, v: str) -> str:
            """Do not allow spaces in field 'username'."""
            if " " in v:
                raise ValueError("username cannot contain spaces")
            return v

        @field_validator("tags")
        @classmethod
        def clean_tags(cls, v: list[str]) -> list[str]:
            """Cleanup of tags in field 'tags'."""
            out = []
            for tag in v:
                t = tag.strip().lower()
                if not t:
                    continue
                out.append(t)
            return out

    a = User(
        id=1, username="elias", email="user@yahoo.gr", tags=["go", "stop"]
    )
    b = a.model_copy()
    b.id = 2
    b.email = "user@google.com"

    a_ops = ModelOps(obj=a)

    UI.print(a_ops.schema())
    UI.print(a_ops.diff(b))
    UI.print(a_ops.model_diff(b))
    UI.print(a_ops.udiff(b))
    UI.print(a_ops.merge(b))
