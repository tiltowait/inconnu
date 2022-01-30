# Troubleshooting

**Inconnu** requires the following permissions:

* **Send Messages:** Should be obvious, no?
* **Use External Emoji:** For displaying individual dice throws and tracker boxes
* **Use Slash Commands:** All of **Inconnu's** commands use slash commands

## Inconnu isn't showing emoji

If **Inconnu** is showing `:hunger: :hunger: :no_hunger: :no_hunger: :no_hunger` or something similar, check that it has the *Use External Emoji* permission for that channel. Additionally, the `@everyone` role requires this permission as well. This is a hard Discord requirement for the slash commands feature that all bots are required to adopt by April 2022.

## Inconnu's replies are blank

Make sure that **Inconnu** has permissions to *Embed Links*. If it does, and only certain users can't see the replies, then affected users must toggle on *Show website preview info from links pasted into chat* under Discord's *Text & Images* settings. If they *still* don't show, then the affected users may be using antivirus software that blocks the embeds. In the past, certain versions of McAfee have been known to do this.
