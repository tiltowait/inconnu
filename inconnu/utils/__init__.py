"""Commonly used utilities."""

from .decorators import not_on_lockdown
from .error import ErrorEmbed, error
from .haven import Haven
from .paramparse import parse_parameters


def raw_command_options(interaction) -> str:
    """Get the options in a command as a dict."""
    options = {}
    for option in interaction.data.get("options", []):
        name = option["name"]
        value = option["value"]
        options[name] = value

    return options


def command_options(interaction) -> str:
    """Format the command options for easy display."""
    options = []
    for option in interaction.data.get("options", []):
        _name = option["name"]
        _value = option["value"]

        # This is hardly exhaustive, since option types can also be members
        # or channels, but the main purpose with enclosing strings in quotes
        # is to remove ambiguity that might occur with more complex string
        # patterns.
        if isinstance(_value, str):
            options.append(f'{_name}="{_value}"')
        else:
            options.append(f"{_name}={_value}")

    return ", ".join(options) if options else "None"
