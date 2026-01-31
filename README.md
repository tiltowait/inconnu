<p align="center">
  <img src="assets/images/inconnu_logo.png" alt="Inconnu Dicebot Logo" width=125 height=125 />
</p>

<p align="center">
  <a href="https://discord.gg/QHnCdSPeEE" title="Join the Inconnu server"><img src="https://img.shields.io/discord/935219170176532580?color=5765F2&label=discord&logo=discord&logoColor=white" alt="Discord member count" /></a>
  <a href="https://www.patreon.com/tiltowait" title="Support me on Patreon!"><img src="https://img.shields.io/endpoint.svg?url=https%3A%2F%2Fshieldsio-patreon.vercel.app%2Fapi%3Fusername%3Dtiltowait%26type%3Dpatrons&style=flat" alt="Patreon" /></a>
  <br>
  <img src="https://img.shields.io/github/v/release/tiltowait/inconnu" alt="Latest release" />
  <img src="https://img.shields.io/github/license/tiltowait/inconnu" alt="MIT license" />
</p>

**Inconnu** is a Discord dicebot for Vampire: The Masquerade 5th Edition. In addition to basic rolls, it offers a number of advanced options and quality-of-life features, such as character integration, trait-based pools, and more. [For a full rundown of **Inconnu's** features, read the documentation.](https://docs.inconnu.app)

## Getting Started

* [Invite Inconnu to your server](https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=537135104&scope=bot%20applications.commands)
* [Official server](https://discord.gg/QHnCdSPeEE)
* [Full documentation](https://docs.inconnu.app)

### Basic Usage

An **Inconnu** roll uses the following syntax: `/roll pool:POOL hunger:HUNGER difficulty:DIFFICULTY`.

*But that's not all!* **Inconnu** tracks character stats, allowing you to write human-readable dice pools, such as *"strength + brawl"*, rather than a simple number. For more information, [check the documentation](https://docs.inconnu.app).

## Required Permissions

* **Send Messages:** For sending update messages in server-configured channels
* **Manage Webhooks:** Used by the [premium "Roleposting" feature](https://docs.inconnu.app/premium/roleposting)

## Troubleshooting

* **Can't use commands?** Make sure **Inconnu** has the permissions above. Additionally, make sure the `@everyone` role has the *Use slash commands* permission.
* **Can't see embeds?** Users need Discord's *Show website preview info from links pasted into chat* setting under *Text & Images* enabled in order to see **Inconnu's** embeds. Some AV software, such as McAfee, have also been known to block embeds.
