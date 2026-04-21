from __future__ import annotations


class CommandError(ValueError):
    pass


def take_flag(args: list[str], flag: str) -> bool:
    present = False
    while flag in args:
        args.remove(flag)
        present = True
    return present


def take_option(
    args: list[str],
    option: str,
    default: str | None = None,
    *,
    required: bool = False,
) -> str:
    if option in args:
        idx = args.index(option)
        if idx + 1 >= len(args):
            raise CommandError(f"Missing value for {option}.")

        value = args[idx + 1]
        if value.startswith("--"):
            raise CommandError(f"Missing value for {option}.")

        del args[idx : idx + 2]
        return value

    if required:
        raise CommandError(f"Missing required option {option}.")

    if default is None:
        raise CommandError(f"No default value configured for {option}.")
    return default


def ensure_no_unknown_args(args: list[str]) -> None:
    if args:
        unknown = " ".join(args)
        raise CommandError(f"Unknown arguments: {unknown}")
