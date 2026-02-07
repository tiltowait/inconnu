"""Emoji manager."""

import asyncio
from typing import TYPE_CHECKING

from discord import AppEmoji
from dotenv import load_dotenv
from loguru import logger

from constants import Damage

if TYPE_CHECKING:
    from bot import InconnuBot

load_dotenv()


class _EmojiManager:
    """Tool for fetching emoji from a given server."""

    def __init__(self):
        self._emojis: dict[str, AppEmoji] = {}
        self.loaded = False
        self._load_triggered = False

    def __getitem__(self, emoji_name: str) -> str:
        standard = {"bp_filled": ":red_circle:​", "bp_unfilled": ":o:​"}
        emoji_map = {
            Damage.NONE.value: "no_dmg",
            Damage.SUPERFICIAL.value: "sup_dmg",
            Damage.AGGRAVATED.value: "agg_dmg",
        }

        if emoji := standard.get(emoji_name):
            # Eventually, we won't need the "standard" emoji set, as everything
            # will be custom
            return emoji + "\u200b"

        emoji_name = emoji_map.get(emoji_name, emoji_name)

        # We attach <0x200b>, a zero-width space, to every emoji. This prevents
        # a weird Android bug where emojis in embeds are gigantic.
        return str(self._emojis[emoji_name]) + "\u200b"

    def get(self, emoji_name, count=1) -> list[str]:
        """Get 'count' copies of an emoji."""
        return [self[emoji_name]] * count

    async def load(self, bot: "InconnuBot"):
        """Load the emoji from the specified guild ."""
        if self._load_triggered or self.loaded:
            return

        self._load_triggered = True

        while not bot.app_emojis:
            logger.info("Waiting for emojis to load")
            await asyncio.sleep(1)

        self._emojis = {emoji.name: emoji for emoji in bot.app_emojis}

        logger.info("Loaded {} app emojis", len(self._emojis))
        logger.debug("{}", list(map(lambda e: e.name, self._emojis.values())))
        self.loaded = True


# Singleton instance
emojis = _EmojiManager()
