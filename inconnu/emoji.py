"""Emoji manager."""

import os

from dotenv import load_dotenv
from loguru import logger

import inconnu

load_dotenv()


class _EmojiManager:
    """Tool for fetching emoji from a given server."""

    def __init__(self):
        self._emojis = {}
        self.loaded = False

    def __getitem__(self, emoji_name: str) -> str:
        standard = {"bp_filled": ":red_circle:​", "bp_unfilled": ":o:​"}
        emoji_map = {
            inconnu.constants.Damage.NONE: "no_dmg",
            inconnu.constants.Damage.SUPERFICIAL: "sup_dmg",
            inconnu.constants.Damage.AGGRAVATED: "agg_dmg",
        }

        if emoji := standard.get(emoji_name):
            # Eventually, we won't need the "standard" emoji set, as everything
            # will be custom
            return emoji + "\u200b"

        emoji_name = emoji_map.get(emoji_name, emoji_name)

        # We attach <0x200b>, a zero-width space, to every emoji. This prevents
        # the weird Android bug where emojis in embeds are gigantic.
        return str(self._emojis[emoji_name]) + "\u200b"

    def get(self, emoji_name, count=1) -> list[str]:
        """Get 'count' copies of an emoji."""
        return [self[emoji_name]] * count

    async def load(self, bot):
        """Load the emoji from the specified guild ."""
        guild = await bot.get_or_fetch_guild(int(os.environ["EMOJI_GUILD"]))
        _emojis = await guild.fetch_emojis()
        self._emojis = {emoji.name: emoji for emoji in _emojis}

        logger.info("EMOJIS: Loaded emojis from %s", guild.name)
        logger.debug("EMOJIS: %s", list(map(lambda e: e.name, self._emojis.values())))
        self.loaded = True


# Singleton instance
emojis = _EmojiManager()
