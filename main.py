"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands

The discord-ui plugin API is potentially unstable and undergoing rapid change.
The current best-working version is v4.2.14
"""

import os

import bot

if __name__ == "__main__":
    bot.setup()
    bot.bot.run(os.environ["INCONNU_TOKEN"])
