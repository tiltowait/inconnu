"""Commonly used utilities."""

from inconnu.utils import decorators
from inconnu.utils.cmdreplace import cmd_replace
from inconnu.utils.decorators import not_on_lockdown
from inconnu.utils.discord_helpers import (
    command_options,
    get_avatar,
    get_message,
    player_lookup,
    raw_command_options,
    re_paginate,
)
from inconnu.utils.paramparse import parse_parameters
from inconnu.utils.permissions import (
    get_or_fetch_supporter,
    is_admin,
    is_approved_user,
    is_supporter,
)
from inconnu.utils.text import (
    clean_text,
    contains_digit,
    de_camel,
    diff,
    fence,
    format_join,
    oxford_list,
    paginate,
    pluralize,
    pull_mentions,
    strtobool,
)

__all__ = (
    "clean_text",
    "cmd_replace",
    "command_options",
    "contains_digit",
    "de_camel",
    "decorators",
    "diff",
    "fence",
    "format_join",
    "get_avatar",
    "get_message",
    "get_or_fetch_supporter",
    "is_admin",
    "is_approved_user",
    "is_supporter",
    "not_on_lockdown",
    "oxford_list",
    "paginate",
    "parse_parameters",
    "player_lookup",
    "pluralize",
    "pull_mentions",
    "raw_command_options",
    "re_paginate",
    "strtobool",
)
