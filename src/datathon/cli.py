from __future__ import annotations

import sys
from collections.abc import Sequence

from rich.table import Table

from datathon.commands.common import CommandError
from datathon.commands.registry import COMMANDS
from datathon.utils.console import console


def _print_root_help() -> None:
    console.print("[bold cyan]Datathon CLI[/bold cyan]")
    console.print("[dim]Usage:[/dim] datathon <command> [options]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Command")
    table.add_column("Description")
    for command, meta in COMMANDS.items():
        table.add_row(command, meta.description)
    table.add_row("help", "Show help for all or one command.")
    console.print(table)
    console.print("[dim]Example:[/dim] uv run datathon build-raw --strict")


def _print_command_help(command: str) -> None:
    command_meta = COMMANDS.get(command)
    if command_meta is not None:
        command_meta.print_help()
        return
    raise CommandError(f"Unknown command '{command}'.")


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help"}:
        _print_root_help()
        return 0

    command = args[0]
    command_args = args[1:]

    if command == "help":
        if command_args:
            try:
                _print_command_help(command_args[0])
            except CommandError as exc:
                console.print(f"[red]Error:[/red] {exc}")
                return 2
            return 0

        _print_root_help()
        return 0

    if "--help" in command_args or "-h" in command_args:
        try:
            _print_command_help(command)
        except CommandError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            return 2
        return 0

    try:
        command_meta = COMMANDS.get(command)
        if command_meta is not None:
            options = command_meta.parse_args(command_args)
            command_meta.run(options)
            return 0

        raise CommandError(f"Unknown command '{command}'.")
    except CommandError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        console.print("Run [bold]datathon --help[/bold] for usage.")
        return 2
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error:[/red] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
