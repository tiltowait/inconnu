---
description: The /roll and /vr commands.
---

# Rolls

New to rolling? Start with [Just the basics](../../guides/quickstart/just-the-basics.md) and [Rolling with traits](../../guides/quickstart/rolling-with-traits.md).

## /roll

```
/roll pool:<pool> hunger:<hunger> difficulty:<difficulty>
```

| Option | Description |
| --- | --- |
| `pool` | Traits (`Strength + Brawl`), numbers, or both. Add `+ Surge` to Blood Surge |
| `hunger` | `Use Current` (0 for mortals and ghouls), or 0–5 |
| `difficulty` | 0–10 |
| `comment` | A description shown with the roll |
| `character` | The character to roll for |
| `player` | The character's owner (admins only) |
| `impairment_category` | Change the roll's [Impairment](impairment.md) category, or ignore Impairment |
| `dice` | `Hide` to [hide your dice](hidden-dice.md) from other players |

## /vr

```
/vr syntax:<pool> [hunger] [difficulty]
```

The same as `/roll`, with the pool, Hunger, and difficulty typed together in `syntax`. It's quicker, especially on mobile, and will feel familiar to Thirst users. `/vr` takes the same other options as `/roll`.

> [!TIP]
> **Example:** Intelligence + Investigation, with current Hunger, at difficulty 3:
>
> ```
> /vr syntax:intelligence+investigation hunger 3
> ```

### Trait shorthand

You only need to type enough of a trait's name to identify it. **Inconnu** finds every trait starting with what you typed; if only one matches, that's the trait.

The standard character sheet has seven traits starting with "S": Science, Stamina, Stealth, Streetwise, Strength, Subterfuge, and Survival. `s` matches all seven, and `st` still matches four, but `sta` matches only Stamina. So this rolls Intelligence + Investigation with current Hunger at difficulty 3:

```
/vr syntax:inte+inv hun 3
```

> [!NOTE]
> Macros save the full trait names, so later traits can't make them ambiguous.

> [!WARNING]
> [Custom traits](../../guides/quickstart/custom-traits.md) count, too. Add a trait called "Staking", and you'll need `stam` for Stamina and `stak` for Staking.
