"""Emoji manager."""

from typing import TYPE_CHECKING

from discord import AppEmoji
from loguru import logger

from constants import Damage, Theme

if TYPE_CHECKING:
    from bot import InconnuBot


class _EmojiManager:
    """Tool for fetching emoji from a given server."""

    def __init__(self):
        self._emojis: dict[str, AppEmoji] = {}
        self.loaded = False

    def emoji(self, theme: Theme, emoji_name: str) -> str:
        """Get an emoji in the given theme."""
        emoji_map = {
            Damage.NONE.value: "no_dmg",
            Damage.SUPERFICIAL.value: "sup_dmg",
            Damage.AGGRAVATED.value: "agg_dmg",
        }
        emoji_name = emoji_map.get(emoji_name, emoji_name)

        # Themes without the emoji fall back to the standard one
        app_emoji = self._emojis.get(f"{theme}_{emoji_name}") if theme else None
        if app_emoji is None:
            app_emoji = self._emojis[emoji_name]

        # We attach <0x200b>, a zero-width space, to every emoji. This prevents
        # a weird Android bug where emojis in embeds are gigantic.
        return str(app_emoji) + "\u200b"

    def get(self, theme: Theme, emoji_name: str, count=1) -> list[str]:
        """Get 'count' copies of an emoji in the given theme."""
        return [self.emoji(theme, emoji_name)] * count

    async def load(self, bot: InconnuBot):
        """Load the emoji from the specified guild ."""
        if self.loaded:
            return

        if bot.app_emojis:
            emojis = bot.app_emojis
        else:
            logger.info("Fetching emojis")
            emojis = await bot.fetch_emojis()

        self._emojis = {emoji.name: emoji for emoji in emojis}

        logger.info("Loaded {} app emojis", len(self._emojis))
        logger.debug("{}", [e.name for e in self._emojis.values()])
        self.loaded = True


# Singleton instance
emojis = _EmojiManager()
