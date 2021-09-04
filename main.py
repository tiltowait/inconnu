"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=346176&scope=bot

The discord-ui plugin API is fairly unstable and undergoing rapid change.
The current best-working version is v4.2.7 (7d7e120608f6bd92a021a1c53f2039f6a0421a77)

Current issues with discord-ui:

* ctx.author.send issues when using a cached context
"""

import os

import commands

if __name__ == "__main__":
    commands.bot.run(os.environ["INCONNU_TOKEN"])
