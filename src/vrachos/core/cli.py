"""Command line interface."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, ClassVar, cast

import click
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


def _get_pydantic_field_default(field_info: FieldInfo) -> Any:
    default = field_info.default
    if default is PydanticUndefined:
        return None
    return default


class Command(BaseModel):
    """Define the command in the command line interface."""

    model_config = ConfigDict(
        populate_by_name=True, arbitrary_types_allowed=False
    )

    NAME: ClassVar[str]
    SUBCOMMANDS_CLS: ClassVar[list[type[Command]]] = []

    @classmethod
    def _get_click_parameters(cls) -> list[click.Option]:
        """Get click parameter options from pydantic fields."""
        params = []
        for field_name, field_info in cls.model_fields.items():
            default = _get_pydantic_field_default(field_info)
            field_type = field_info.annotation
            field_description = (
                field_info.description + "."
                if field_info.description
                and not field_info.description.endswith(".")
                else field_info.description
            )

            # Construct argument flag(s)
            flags = [f"--{field_name}"]
            if field_info.alias and field_info.alias != field_name:
                flags.append(f"-{field_info.alias}")

            option_kwargs: dict[str, Any] = {}
            # boolean is special
            if field_type is bool:
                option_kwargs["is_flag"] = True

            # Assign parameter
            if field_type in (bool, int, float, str):
                if default is not None:
                    option_kwargs["default"] = default
                    option_kwargs["required"] = False
                else:
                    option_kwargs["required"] = True

                option_kwargs["help"] = field_description
                params.append(click.Option(flags, **option_kwargs))
            else:
                raise NotImplementedError(
                    f"Field: {field_name} | {field_info}"
                )

        return params

    @classmethod
    def _build_hierarchy(cls, ctx: click.Context) -> dict[str, Any]:
        """Build nested SimpleNamespace hierarchy from a click context."""
        params = {}
        current_ctx: click.Context | None = ctx
        while current_ctx:
            if cls is current_ctx.obj:
                for param_key in current_ctx.params:
                    params[param_key] = current_ctx.params[param_key]
            else:
                if cls in current_ctx.obj.SUBCOMMANDS_CLS:
                    obj = current_ctx.obj(**current_ctx.params)
                    params[obj.NAME] = current_ctx.obj._build_hierarchy(
                        current_ctx
                    )
            current_ctx = current_ctx.parent

        return params

    @classmethod
    def _handler(cls, **kwargs: Any) -> None:
        """Handle click command invocation."""
        context = click.get_current_context()
        args = SimpleNamespace(**cls._build_hierarchy(context))
        obj = cls(**kwargs)

        obj.on_init(args=args)
        if context.invoked_subcommand is None:
            obj.on_run(args=args)

    @classmethod
    def _as_click(cls) -> click.Command | click.Group:
        """Convert the pydantic model into a click command."""
        subcommands: list[click.Command | click.Group] = []
        for subcommand_cls in cls.SUBCOMMANDS_CLS:
            subcommand_click_obj = subcommand_cls._as_click()
            if subcommand_click_obj:
                subcommands.append(subcommand_click_obj)

        params = cls._get_click_parameters()
        help_msg = cls.__doc__
        click_obj: click.Command | click.Group
        if cls.SUBCOMMANDS_CLS:
            click_obj = click.Group(
                name=cls.NAME,
                help=help_msg,
                params=cast(list[click.Parameter], params),
                callback=cls._handler,
                invoke_without_command=True,
                context_settings={"obj": cls},
            )
            for subcommand in subcommands:
                click_obj.add_command(subcommand)
        else:
            click_obj = click.Command(
                name=cls.NAME,
                help=help_msg,
                params=cast(list[click.Parameter], params),
                callback=cls._handler,
                context_settings={"obj": cls},
            )

        return click_obj

    @classmethod
    def _get_help(cls) -> None:
        """Print the help message."""
        context = click.get_current_context()
        click.echo(context.get_help())

    @classmethod
    def run(cls) -> None:
        """Run the command."""
        click_obj = cls._as_click()
        click_obj()

    def on_init(self, args: SimpleNamespace) -> None:
        """
        Initialise the command.

        This is called with order of call if this command is part of a nested
        chain.
        """
        ...

    def on_run(self, args: SimpleNamespace) -> None:
        """Run the command."""
        type(self)._get_help()
        ...


if __name__ == "__main__":

    class TicketCreateCommand(Command):
        """Create a ticket."""

        NAME = "create"

        key: str = Field(
            description="The ticket's unique key",
        )

        def on_run(self, args: SimpleNamespace) -> None:
            """Run the command."""
            print(f"{self.NAME} {self=} {args=}")

    class TicketCommand(Command):
        """List tickets."""

        NAME = "ticket"
        SUBCOMMANDS_CLS = [TicketCreateCommand]

        filter: str = Field(
            "default",
            description="The ticket filter",
        )

        def on_run(self, args: SimpleNamespace) -> None:
            """Run the command."""
            print(f"{self.NAME} {self=} {args=}")

    class AppCommand(Command):
        """App command."""

        NAME = "app"
        SUBCOMMANDS_CLS = [TicketCommand]

        verbose: bool = Field(False, description="Verbose output", alias="v")
        debug: bool = Field(True, description="Debug output", alias="d")

        def on_run(self, args: SimpleNamespace) -> None:
            """Run the command."""
            print(f"{self.NAME} {self=} {args=}")

    AppCommand.run()
