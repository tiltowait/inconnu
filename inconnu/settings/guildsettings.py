"""settings/guildsettings.py - Guild-wide settings class."""

from enum import Enum



class GuildSettings:
    """
    A container class that represents guild settings.
    NOTE: It does *NOT* handle any database manipulation!
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, parameters):
        settings = parameters.get("settings", {})

        self.accessibility = settings.get("accessibility", False)
        self.experience_permissions = settings.get("experience_permissions", ExpPerms.UNRESTRICTED)
        self.oblivion_stains = settings.get("oblivion_stains", [1, 10])
        self.update_channel = settings.get("update_channel")


class ExpPerms(str, Enum):
    """An enum for experience adjustment permissions."""

    UNRESTRICTED = "unrestricted"
    UNSPENT_ONLY = "unspent_only"
    LIFETIME_ONLY = "lifetime_only"
    ADMIN_ONLY = "admin_only"
