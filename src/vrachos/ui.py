"""User interface."""

from __future__ import annotations

import json
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, TypeVar, cast, overload

from pydantic import BaseModel
from rich.console import Console
from rich.live import Live
from rich.pretty import Pretty
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.traceback import install

from .core.io import open_editor
from .experimental.common import (
    get_model_defaults_json,
    get_model_json,
    is_unified_diff,
    is_user_defined_instance,
)

_T = TypeVar("_T", bound=BaseModel)
_SimpleType = TypeVar("_SimpleType", str, int, float, bool)


class UI:
    """Command line user interface."""

    console = Console(record=True)
    THEME = "monokai"

    @overload
    @classmethod
    def prompt(cls, model: type[_T]) -> _T: ...

    @overload
    @classmethod
    def prompt(cls, model: _T) -> _T: ...

    @overload
    @classmethod
    def prompt(cls, model: type[_SimpleType]) -> _SimpleType: ...

    @overload
    @classmethod
    def prompt(cls, model: _SimpleType) -> _SimpleType: ...

    @overload
    @classmethod
    def prompt(cls, model: dict[str, str]) -> dict[str, str]: ...

    @classmethod
    def prompt(cls, model: Any, choices: list[Any] | None = None) -> Any:
        """Prompt user for model input."""
        default: str | None = None

        # Determine the type and default value
        if isinstance(model, dict):
            default = json.dumps(model, indent=4)
            user_str = open_editor(default or "")
            try:
                return json.loads(user_str)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {exc}")
                raise
        elif isinstance(model, type) and issubclass(model, BaseModel):
            default = get_model_defaults_json(model)
            user_str = open_editor(default or "")
            try:
                user_dict = json.loads(user_str)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {exc}")
                raise
            return model(**user_dict)
        elif isinstance(model, BaseModel):
            default = get_model_json(model)
            user_str = open_editor(default or "")
            try:
                user_dict = json.loads(user_str)
            except json.JSONDecodeError as exc:
                print(f"Invalid JSON: {exc}")
                raise
            return type(model)(**user_dict)
        else:
            # Handle simple types (str, int, float, bool)
            model_type = type(model) if not isinstance(model, type) else model
            if not isinstance(model, type):
                default = str(model)

            user_str = cast(
                str,
                Prompt.ask(
                    f"\\[[yellow]{model_type.__name__}[/yellow]] Enter value:",
                    default=default or "",
                ),
            )
            try:
                return model_type(user_str)
            except ValueError as exc:
                print(f"Invalid input: {exc}")
                raise

    @classmethod
    def print(cls, data: Any) -> None:
        """Pretty print data with syntax highlighting."""
        if isinstance(data, dict):
            json_str = json.dumps(data, indent=4)
            syntax = Syntax(
                json_str, "json", theme=cls.THEME, line_numbers=False
            )
            cls.console.print(syntax)
        elif isinstance(data, str):
            if is_unified_diff(data):
                syntax = Syntax(
                    data, "diff", theme=cls.THEME, line_numbers=False
                )
                cls.console.print(syntax)
            else:
                cls.console.print(data)
        elif isinstance(data, BaseModel):
            cls.console.print(
                Syntax(
                    data.model_dump_json(indent=4),
                    "json",
                    theme=cls.THEME,
                    line_numbers=False,
                    word_wrap=False,
                )
            )
        elif isinstance(data, type):
            from rich import inspect

            inspect(
                data,
                methods=True,
                dunder=False,
                all=False,
                private=False,
                docs=True,
                value=False,
                console=cls.console,
            )
        elif is_user_defined_instance(data):
            print(data)
        else:
            cls.console.print(Pretty(data))

    @staticmethod
    def init() -> None:
        """Install Rich traceback globally."""
        width = shutil.get_terminal_size().columns
        install(
            theme="monokai", show_locals=True, locals_max_length=3, width=width
        )

    @staticmethod
    @contextmanager
    def spinner(message: str = "Processing...") -> Generator[None]:
        """
        Context manager that displays a spinner while code executes.

        Args:
            message: Message to display next to the spinner.

        Yields:
            None

        Example:
            with __UI__.with_spinner("Loading data..."):
                time.sleep(2)
        """
        spinner = Spinner("runner", text=message)
        with Live(spinner, console=UI.console, refresh_per_second=12.5):
            yield


if __name__ == "__main__":

    from datetime import UTC, datetime

    from pydantic import Field

    UI.init()

    class User(BaseModel):
        """User model."""

        id: int = Field(..., ge=1)
        username: str = Field(..., min_length=3, max_length=32)
        email: str
        tags: list[str] = Field(default_factory=list)
        created_at: datetime = Field(
            default_factory=lambda: datetime.now(tz=UTC)
        )

    user_1: User = UI.prompt(User)
    UI.print(f"Type = {type(user_1)}")
    UI.print(user_1)

    user = User(
        id=1, username="user", email="user@email.com", tags=["go", "stop"]
    )
    user_2: User = UI.prompt(user)
    UI.print(f"Type = {type(user_2)}")
    UI.print(user_2)
