---
description: Learn about Inconnu's customization options.
---

# ⚙️ Server Settings

**Inconnu** has a few customizable behaviors, which are adjustable using the `/settings set` command available to server administrators. Anyone can use the `/settings show` command to see the server's current configuration. Read below for an explanation of the parameters.

### `experience_permissions`

> [!NOTE]
> **Default:** `Unrestricted`

This parameter specifies whether users may edit their own XP totals. The options are `Unrestricted`, `Unspent XP only`, `Lifetime XP only`, and `Restricted (admins only)`.

**Recommended reading:** `/experience` commands.

### `oblivion_stains`

> [!NOTE]
> **Default:** `1s and 10s (RAW)`

When making a Rouse check, you may have noticed an occasional message informing you to apply a stain if it was an Oblivion roll. This is due to the rule introduced in _Chicago by Night_ and _Cults of the Blood Gods_ that a Rouse check for an Oblivion power, Ritual, or Ceremony grants a Stain on a 1 or a 10.

With the `oblivion_stains` parameter, you may customize this behavior to only show the message on 10s, 1s, or never.

> [!NOTE]
> **This parameter affects macros.** Macros created with the `staining` parameter set to `Yes` will automatically apply a stain should the Rouse check result in the value chosen here.

### `update_channel`

> [!NOTE]
> **Default:** `None`

**Inconnu** uses ephemeral messages to communicate with players when they update their characters. While this saves on clutter, it means that server administrators can't see what's happening. With this parameter set, **Inconnu** will list character updates in a single location—helpful if you have a less scrupulous player who decides to set all their traits to 5s!

### `add_empty_resonance`

> [!NOTE]
> **Default:** `No`

When the Oblivion Discipline was added, it came with a new Resonance, called "Empty". Unfortunately, Empty Resonance was never added to the table of random Resonances. With this parameter enabled, the `/resonance` command will add Empty Resonance to its list of possible random Resonances.

### `accessibility`

> [!NOTE]
> **Default:** `No`

This enables or disables accessibility mode for the entire server. Users may not override this parameter if set to `Yes`.

### `max_hunger`

> [!NOTE]
> **Default:** `5`

An experimental setting, this allows you to increase the max Hunger rating in rolls from 5 to 10. Note that, at present, this has no effect on characters' max Hunger.
