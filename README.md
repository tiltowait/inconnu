<p align="center">
  <img src="images/inconnu_logo.png" alt="Inconnu Dicebot" width=125 height=125 />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Pycord-2.0.0-blue" alt="Requires Pycord 2.0" />
  <img src="https://img.shields.io/badge/pymongo-3.12.0-yellow" alt="Requires pymongo 3.12.0" />
  <img src="https://img.shields.io/badge/python-3.10.1-green" alt="Uses Python 3.10.1" />
</p>

**Inconnu** is a Discord dicebot for Vampire: The Masquerade 5th Edition. In addition to basic rolls, it offers a number of advanced options and quality-of-life features, such as character integration, trait-based pools, and more. [For a full rundown of **Inconnu's** features, read the documentation.](https://www.inconnu-bot.com)

## Getting Started

* **Invite Inconnu to your server:** [Link](https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=2147764224&scope=applications.commands%20bot)
* **Demo/Support server:** [Link](https://discord.gg/CPmsdWHUcZ)
* **Full documentation:** [Link](https://www.inconnu-bot.com/#/)

### Basic Usage

An **Inconnu** roll uses the following syntax: `/vr syntax:<pool> [hunger] [difficulty]`. While `pool` is required, `hunger` and `difficulty` are optional and default to `0` if omitted. (Alternatively, you may use the `/roll` command, which takes a little longer to type in but requires each parameter.)

*But that's not all!* **Inconnu** offers trait-based pools, allowing you to write human-readable pools, such as *"strength + brawl"* rather than a simple number. For more infomration, [check the documentation](https://www.inconnu-bot.com).

## Required Permissions

* **Send Messages:** Should be obvious, no?
* **Embed Links:** Used in most of the bot's replies
* **Use External Emoji:** For displaying individual dice throws and tracker boxes
* **Use Slash Commands**

## Troubleshooting

* **Can't use commands?** Make sure **Inconnu** has the permissions above. Additionally, make sure the `@everyone` role has the *Use slash commands* permission.
* **Emojis not working?** Make sure to enable the *Use External Emoji* permission. Alternatively, enable [accessibility mode](https://www.inconnu-bot.com/#/accessibility).
* **Can't see embeds?** You need the *Show website preview info from links pasted into chat* setting under *Text & Images* enabled in order to see **Inconnu's** embeds. Some AV software, such as McAfee, have also been known to block embeds.
