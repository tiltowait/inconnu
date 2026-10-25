"""Service layer for bot infrastructure."""

from services import settings, wizard
from services.characters import CharacterManager, char_mgr
from services.emoji import emojis
from services.guildcache import guild_cache
from services.log import report_database_error
from services.reporter import ErrorReporter, post_update
from services.webhooks import WebhookCache

wizard_cache = wizard.WizardCache()

__all__ = (
    "CharacterManager",
    "ErrorReporter",
    "WebhookCache",
    "char_mgr",
    "emojis",
    "guild_cache",
    "post_update",
    "report_database_error",
    "settings",
    "wizard",
    "wizard_cache",
)
