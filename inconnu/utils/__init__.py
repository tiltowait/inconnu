"""Commonly used utilities."""

from inconnu.utils import decorators
from inconnu.utils.cmdreplace import cmd_replace
from inconnu.utils.decorators import not_on_lockdown
from inconnu.utils.discord_helpers import (
    command_options,
    get_avatar,
    get_message,
    raw_command_options,
    re_paginate,
)
from inconnu.utils.embeds import VCharEmbed
from inconnu.utils.error import ErrorEmbed, error
from inconnu.utils.haven import Haven
from inconnu.utils.paramparse import parse_parameters
from inconnu.utils.permissions import (
    get_or_fetch_supporter,
    is_admin,
    is_approved_user,
    is_supporter,
)
from inconnu.utils.text import (
    clean_text,
    de_camel,
    diff,
    fence,
    format_join,
    oxford_list,
    pull_mentions,
)

__all__ = (
    "clean_text",
    "cmd_replace",
    "command_options",
    "de_camel",
    "decorators",
    "diff",
    "ErrorEmbed",
    "error",
    "fence",
    "format_join",
    "get_avatar",
    "get_message",
    "get_or_fetch_supporter",
    "Haven",
    "is_admin",
    "is_approved_user",
    "is_supporter",
    "not_on_lockdown",
    "oxford_list",
    "parse_parameters",
    "pull_mentions",
    "raw_command_options",
    "re_paginate",
    "VCharEmbed",
)
