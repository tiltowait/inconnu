---
description: Roll without showing everyone your dice.
---

# Hidden dice

`/vr`, `/roll`, and `/vm` take a `dice` option. Set it to `Hide` to keep your dice to yourself:

```
/vr syntax:dex+stealth hunger 3 dice:Hide
```

### Who sees what

| | You | Other players | Update channel |
| --- | --- | --- | --- |
| Outcome and successes | ✓ | ✓ | ✓ |
| Margin and Difficulty | ✓ | ✓ | ✓ |
| Pool | ✓ | Traits only¹ | ✓ |
| Updates (Surge, re-roll, Willpower) | ✓ | ✓ | ✓ |
| Comment | ✓ | ✓ | ✓ |
| Dice and Hunger | ✓ | | ✓ |
| Impairment penalty and reminders | ✓ | | ✓ |
| Re-roll and Surge buttons | ✓ | | |

¹ A pool written only as numbers, such as `7`, shows as `Hidden`, since it would reveal the pool's size.

You get the full roll in a message only you can see, along with the usual buttons. When you re-roll or Surge, every copy of the roll updates. A Surge's Rouse check, the Willpower you spend, and any Slake menu are shown only to you.

If the server has a [character updates channel](../../advanced/server-settings.md#character-updates-channel), the full roll is posted there with a link to the public one, so your Storyteller can see your dice.

### Server permissions

Server admins choose who may hide their dice in [`/settings scope:Server`](../../advanced/server-settings.md#hidden-dice). If you're not allowed to, **Inconnu** tells you before rolling anything, including a macro's Rouse checks.
