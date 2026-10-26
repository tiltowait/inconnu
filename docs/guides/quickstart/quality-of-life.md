---
description: The commands you'll use during play.
---

# Quality of life

Before we wrap up, let's look at the commands you'll use during a session.

## Awakening

At the start of each session, run `/awaken`. Your character heals Superficial Willpower damage equal to the higher of their Composure or Resolve. Vampires then make a Rouse Check, mortals heal Superficial Health damage equal to their Stamina, and ghouls heal twice that.

Need to pass for human? `/bol` makes the Blush of Life's Rouse Check, accounting for your Humanity: at Humanity 8 you re-roll it, and at 9 or 10 you don't need one at all.

## Rousing the blood

When a power calls for a Rouse Check, use `/rouse`; it raises your Hunger on a failure. You can set how many checks to make (`count`), whether to re-roll failures (`reroll`), and what the check is for (`purpose`).

## Slaking Hunger

After your character feeds, use `/slake` to lower their Hunger.

> [!NOTE]
> **What about frenzy?** If you slake at Hunger 4 or 5, you'll see a red **Hunger Frenzy** button. If your Storyteller calls for a frenzy check, click it.

## Humanity and Remorse

Use `/stain` to add or remove Stains.

When your Storyteller calls for a Remorse Check, use `/remorse`. It rolls one die per unmarked Humanity box (minimum 1). Succeed, and your Humanity holds; fail, and it drops by 1. Either way, your Stains are cleared.

> [!NOTE]
> **Opting to fail?** If you're allowed to, lower your Humanity with `/character adjust humanity:`. That clears your Stains, too.

## Frenzy

A frenzy check rolls your unspent Willpower plus a third of your Humanity. `/frenzy` does the math; just give it a Difficulty.

> [!NOTE]
> **Bonuses and penalties?** `/frenzy`'s optional parameters cover clan Banes and powers that affect the roll. Most players won't need them.

