<p align="center">
  <img src="images/inconnu_logo.png" alt="Inconnu Dicebot Logo" width=125 height=125 />
</p>

<p align="center">
  <a href="https://discord.gg/QHnCdSPeEE" title="Join the Inconnu server"><img src="https://img.shields.io/discord/935219170176532580?color=5765F2&label=discord&logo=discord&logoColor=white" alt="Discord member count" /></a>
  <img src="https://img.shields.io/github/v/release/tiltowait/inconnu" alt="Latest release" />
  <img src="https://img.shields.io/github/license/tiltowait/inconnu" alt="MIT license" />
</p>

**Inconnu** is a Discord dicebot for Vampire: The Masquerade 5th Edition. In addition to basic rolls, it offers a number of advanced options and quality-of-life features, such as character integration, trait-based pools, and more. [For a full rundown of **Inconnu's** features, read the documentation.](https://www.inconnu.app)

## Getting Started

* **Invite Inconnu to your server:** [Link](https://discord.com/api/oauth2/authorize?client_id=882409882119196704&permissions=537135104&scope=bot%20applications.commands)
* **Demo/Support server:** [Link](https://discord.gg/QHnCdSPeEE)
* **Full documentation:** [Link](https://docs.inconnu.app)

### Basic Usage

An **Inconnu** roll uses the following syntax: `/vr syntax:<pool> [hunger] [difficulty]`. While `pool` is required, `hunger` and `difficulty` are optional and default to `0` if omitted. (Alternatively, you may use the `/roll` command, which takes a little longer to type in but requires each parameter.)

*But that's not all!* **Inconnu** offers trait-based pools, allowing you to write human-readable pools, such as *"strength + brawl"* rather than a simple number. For more infomration, [check the documentation](https://www.inconnu.app).

## Required Permissions

* **Send Messages:** Necessary for sending messages
* **Use External Emoji:** For displaying individual dice throws and tracker boxes
* **Manage Webhooks:** Necessary for the premium `/post` feature (upcoming)

## Troubleshooting

* **Can't use commands?** Make sure **Inconnu** has the permissions above. Additionally, make sure the `@everyone` role has the *Use slash commands* permission.
* **Emojis not working?** Make sure to enable the *Use External Emoji* permission. Alternatively, enable [accessibility mode](https://docs.inconnu.app/command-reference/miscellaneous#accessibility-mode).
* **Can't see embeds?** You need the *Show website preview info from links pasted into chat* setting under *Text & Images* enabled in order to see **Inconnu's** embeds. Some AV software, such as McAfee, have also been known to block embeds.
