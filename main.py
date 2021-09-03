"""
main.py - Start up the bot and perform any last-minute configuration.
Invite: https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=346176&scope=bot
"""

import os

import commands

if __name__ == "__main__":
    commands.bot.run(os.environ["INCONNU_TOKEN"])
