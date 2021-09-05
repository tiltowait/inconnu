"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=346176&scope=bot

The discord-ui plugin API is fairly unstable and undergoing rapid change.
The current best-working version is v4.2.8 (5b948542f519b35ec7233749016044735b374c61)
"""

import os

import commands

if __name__ == "__main__":
    commands.setup()
    commands.bot.run(os.environ["INCONNU_TOKEN"])
