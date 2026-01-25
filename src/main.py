"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands
"""

import os

import discord
import uvloop
from dotenv import load_dotenv
from loguru import logger

import bot

load_dotenv()


# Patch discord.Interaction
def respond(self, *args, **kwargs):
    """Returns either the InteractionResponse or followup's send method."""
    if self.response.is_done():
        return self.followup.send(*args, **kwargs)
    return self.response.send_message(*args, **kwargs)


def main():
    uvloop.install()
    logger.info("Installed uvloop")

    discord.Interaction.respond = respond
    logger.info("Patched discord.Interaction")

    bot.bot.run(os.environ["INCONNU_TOKEN"])


if __name__ == "__main__":
    main()
