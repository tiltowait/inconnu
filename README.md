<p align="center">
  <img src="images/inconnu_logo.png" alt="Inconnu Dicebot" width=125 height=125 />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/discord.py-1.7.3-brightgreen" alt="Requires discord.py v1.7.3" />
  <img src="https://img.shields.io/badge/discord--ui-4.2.14-blue" alt="Requires discord-ui v4.2.14" />
  <img src="https://img.shields.io/badge/psycopg2-2.8.6-yellow" alt="Requires psycopg2 v2.8.6" />
  <img src="https://img.shields.io/badge/python-3.9.6-9cf" alt="Requires python 3.9.6" />
</p>

**Inconnu** is a Discord dicebot for Vampire: The Masquerade 5th Edition. In addition to basic rolls, it offers a number of advanced options and quality-of-life features, such as character integration, trait-based pools, and more. [For a full rundown of **Inconnu's** features, read the documentation.](https://www.inconnu-bot.com)

## Getting Started

Add **Inconnu** to your server by following [this link](https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147829760&scope=bot%20applications.commands). A demo server will be created soon.

### Basic Usage

An **Inconnu** roll uses the following syntax: `//v <pool> [hunger] [difficulty]`. While `pool` is required, `hunger` and `difficulty` are optional and default to `0` if omitted.

*But that's not all!* **Inconnu** offers trait-based pools, allowing you to write human-readable pools, such as *"strength + brawl"* rather than a simple number. For more infomration, [check the documentation](https://www.inconnu-bot.com).

## Required Permissions

* **Send Messages:** Should be obvious, no?
* **Embed Links:** Used for roll display (outside of compact mode), initiative, help display, etc.
* **Read Message History:** Used for the reply feature
* **Use External Emoji:** For displaying individual dice throws
* **Use Slash Commands:** For future-proofing due to impending Discord changes
