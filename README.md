<p align="center">
  <img src="images/inconnu_logo.png" alt="Inconnu Dicebot" width=125 height=125 />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/discord.py-2.0.0_alpha-brightgreen" alt="Requires discord.py v2.0.0 alpha" />
  <img src="https://img.shields.io/badge/discord--ui-4.3.8-blue" alt="Requires discord-ui v5.0.1" />
  <img src="https://img.shields.io/badge/pymongo-3.12.0-yellow" alt="Requires pymongo v3.12.0" />
  <img src="https://img.shields.io/badge/python-3.9.6-9cf" alt="Requires python 3.9.6" />
</p>

**Inconnu** is a Discord dicebot for Vampire: The Masquerade 5th Edition. In addition to basic rolls, it offers a number of advanced options and quality-of-life features, such as character integration, trait-based pools, and more. [For a full rundown of **Inconnu's** features, read the documentation.](https://www.inconnu-bot.com)

## Getting Started

* **Invite Inconnu to your server:** [Link](https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands)
* **Demo server:** [Link](https://discord.gg/CPmsdWHUcZ)

### Basic Usage

An **Inconnu** roll uses the following syntax: `/vr <pool> [hunger] [difficulty]`. While `pool` is required, `hunger` and `difficulty` are optional and default to `0` if omitted.

*But that's not all!* **Inconnu** offers trait-based pools, allowing you to write human-readable pools, such as *"strength + brawl"* rather than a simple number. For more infomration, [check the documentation](https://www.inconnu-bot.com).

## Required Permissions

* **Send Messages:** Should be obvious, no?
* **Embed Links:** Used in most of the bot's replies
* **Read Message History:** Used for the reply feature
* **Use External Emoji:** For displaying individual dice throws and tracker boxes
* **Use Slash Commands**

## Troubleshooting

**Inconnu** is currently migrating to Discord's slash command system, and there may be some minor hiccups until this process is complete. **If emojis aren't showing**, check the server/channel permissions. Both **Inconnu** *and* the `@everyone` role need `Use External Emoji` permissions! This is a hard requirement by Discord that will affect *all* bots come April 2022.

Users need the *Show website preview info from links pasted into chat* setting under *Text & Images* enabled in order to see **Inconnu's** embeds. Some AV software, such as McAfee, have also been known to block embeds.
