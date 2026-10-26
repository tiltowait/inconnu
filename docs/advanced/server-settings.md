---
description: Learn about Inconnu's customization options.
---

# Settings

**Inconnu** has personal settings and server settings, both shown in a menu:

```
/settings scope:<Yourself/Server>
```

Anyone can change their own settings, which follow them across servers. Anyone can view the server settings, but only server admins can change them.

## Your settings

### Use emojis

> [!NOTE]
> **Default:** `Yes`

Use custom emojis for dice and trackers. When off, **Inconnu** uses plain text instead. If the server turns emojis off, they're off for everyone.

### Automatically apply Impairment

> [!NOTE]
> **Default:** `Yes`

Subtract [Impairment](../command-reference/rolls/impairment.md) penalties from your rolls automatically. When off, **Inconnu** reminds you of your Impairment instead. The `impairment_category` roll option still applies a penalty either way.

## Server settings

### Use emojis (server)

> [!NOTE]
> **Default:** `Yes`

Turns custom emojis off for the whole server. Players can't turn them back on for themselves.

### Hidden dice

> [!NOTE]
> **Default:** `Anyone can hide their dice`

Who may use `dice:Hide` to [hide their dice](../command-reference/rolls/hidden-dice.md) from other players. The options are:

* Anyone can hide their dice
* Only admins can hide their dice
* No one can hide their dice (this includes admins)

### Resonance mode

> [!NOTE]
> **Default:** `Use V5 core distribution`

The Resonance probabilities `/resonance` uses:

* **Use V5 core distribution**
* **Use alternate distribution from Tattered Facade**
* **Add 16.7% chance for Empty Resonance:** The core distribution, plus a chance of Empty Resonance, which came with the Oblivion Discipline but never made it into the core table

### Oblivion Stains

> [!NOTE]
> **Default:** `1s and 10s (RAW)`

_Chicago by Night_ and _Cults of the Blood Gods_ say a Rouse Check for an Oblivion power, Ritual, or Ceremony grants a Stain on a 1 or a 10. **Inconnu** reminds players of this after Rouse Checks. This setting changes when it does: on `1s and 10s (RAW)`, `1s only`, `10s only`, or `Never`.

> [!NOTE]
> **This setting affects macros.** Macros created with `staining:Yes` automatically apply a Stain when the Rouse Check matches this setting.

### Max Hunger

> [!NOTE]
> **Default:** `5 (RAW)`

Raises the maximum Hunger in rolls from 5 to 10. It doesn't change characters' maximum Hunger.

### Experience

> [!NOTE]
> **Default:** `Players can adjust unspent and lifetime XP`

Whether players can edit their own XP. The options are:

* Players can adjust unspent and lifetime XP
* Players can adjust unspent XP only
* Players can adjust lifetime XP only
* Only admins can adjust XP

**Recommended reading:** [Experience Management](administration/experience-management.md).

### Character updates channel

> [!NOTE]
> **Default:** None

**Inconnu** tells players about their character updates privately. That saves clutter, but it means admins can't see what's happening. Set a channel, and **Inconnu** also posts there:

* Character updates, such as Trait and tracker changes
* Willpower spent on re-rolls
* The full results of [hidden rolls](../command-reference/rolls/hidden-dice.md)

### Rolepost changelog channel

> [!NOTE]
> **Default:** None

Where **Inconnu** posts when someone edits a `/post`. See [Changelog channel](../premium/roleposting.md#changelog-channel).

### Rolepost deletion channel

> [!NOTE]
> **Default:** None

Where **Inconnu** posts when a `/post` is deleted. See [Deletion channel](../premium/roleposting.md#deletion-channel).
