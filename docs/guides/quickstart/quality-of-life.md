---
description: >-
  Inconnu features a variety of quality-of-life features. On this page, we'll
  take a look at just a few of them.
---

# 💙 Quality of life

Before we conclude, let's take a look at a few common tasks.

### Awakening

When your character wakes for the session, you heal Superficial Willpower damage equal to the higher of your Composure or Resolve. Vampires make a single Rouse check. Mortals heal Superficial Health damage equal to their Stamina, and ghouls heal twice that. **Inconnu** lets you do all this with a single command: `/awaken`.

Finally, you may invoke the Blush of Life with the `/bol` command, which takes your character's Humanity into account: Humanity 8 gets to re-roll the Rouse check, and Humanity 9 and 10 don't need to Rouse at all. Speaking of Rouses ...

### Rousing the blood

**Inconnu** can perform a Rouse check and automatically update your Hunger with a single command: `/rouse`. This command has several optional parameters allowing you to specify the `count` of Rouse checks to make, whether failures should be `reroll`ed, and the `purpose` of the check.

### Slaking hunger

Rather than issuing lengthy `/character adjust` commands to set your Hunger level every time your character feeds, you can use the `/slake` command.

> [!NOTE]
> **What about frenzy?** If you slake Hunger while at Hunger 4 or 5, the `/slake` message will show a red **Hunger Frenzy** button. Clicking this button, if the Storyteller tells you to, will automatically perform a frenzy check at the indicated DC.

### Humanity and Remorse

Use the `/stain` command to quickly add or remove Stains to or from your character's Humanity.

When your Storyteller tells you to, you can perform a Remorse Check by entering `/remorse`. This rolls a number of dice equal to the number of unmarked Humanity boxes (minimum 1). If successful, your Humanity stays the same. If unsuccessful, your Humanity automatically decreases by 1. In either case, your Stains are wiped clean.

> [!NOTE]
> **Opting to fail?** If the situation allows you to opt to fail, you can manually reduce your Humanity rating with `/character adjust humanity:`. Doing this will automatically clear any Stains you have.

### Frenzy

In V5, a frenzy check comprises unspent Willpower plus one-third of the character's Humanity rating. Rather than making you do math, **Inconnu** can do it for you with the `/frenzy` command. Simply specify a difficulty and roll the dice.

> [!NOTE]
> **Bonuses and penalties?** `/frenzy`'s optional parameters allow you to specify bonuses and penalties to the frenzy's dice pool. For most users, these parameters can be safely ignored.

